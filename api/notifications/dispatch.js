import crypto from "node:crypto";
import {devices, received, markReceived, lockDispatch, unlockDispatch, removeDevice, pushStorageConfigured} from "../../lib/push-redis.js";
import {sendPush, apnsConfigured} from "../../lib/apns-client.js";

function tokenValid(req) {
  const expected = String(process.env.PUSH_DISPATCH_SECRET || "");
  const supplied = String(req.headers.authorization || "").replace(/^Bearer\s+/i, "");
  if (expected.length < 32 || expected.length !== supplied.length) return false;
  return crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(supplied));
}

async function loadBatch() {
  const repo = process.env.ADMIN_GITHUB_REPO || "Chethan-Mns/Hdcareers";
  const ref = process.env.ADMIN_GITHUB_BASE || "main";
  const token = process.env.GITHUB_PUBLISH_TOKEN;
  if (!token) throw new Error("GitHub read access not configured.");
  const response = await fetch("https://api.github.com/repos/" + repo +
    "/contents/data/daily-review-batch.json?ref=" + encodeURIComponent(ref), {
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: "Bearer " + token,
      "User-Agent": "HD-Careers-Push-Dispatcher"
    },
    cache: "no-store"
  });
  if (!response.ok) throw new Error("Could not fetch the latest batch.");
  const file = await response.json();
  return JSON.parse(Buffer.from(String(file.content || "").replace(/\n/g, ""), "base64").toString("utf8"));
}

export default async function handler(req, res) {
  res.setHeader("Cache-Control", "private, no-store");
  if (req.method !== "POST") return res.status(405).json({error: "Method not allowed."});
  if (!tokenValid(req)) return res.status(401).json({error: "Authentication required."});
  if (!pushStorageConfigured() || !apnsConfigured()) {
    return res.status(503).json({error: "APNs or device storage is not configured."});
  }

  let lockedBatch = "";
  try {
    const batch = await loadBatch();
    const id = String(batch?.batchId || "");
    const generated = Date.parse(batch?.generatedAt || "");
    if (!/^[a-zA-Z0-9_-]{6,100}$/.test(id) ||
        !Array.isArray(batch.priority) || batch.priority.length !== 10 ||
        !Array.isArray(batch.backup) || batch.backup.length !== 10 ||
        !Number.isFinite(generated) ||
        generated > Date.now() + 300000 || generated < Date.now() - 48 * 3600000) {
      return res.status(409).json({error: "No recent complete 20-job review batch is ready."});
    }
    if (!(await lockDispatch(id))) return res.status(409).json({error: "This batch is already dispatching."});
    lockedBatch = id;
    const registered = await devices();
    if (!registered.length) return res.status(409).json({error: "No iPhone registered for remote push."});
    const results = [];
    for (const device of registered) {
      if (await received(id, device.id)) {
        results.push({deviceId: device.id, state: "already-notified"});
        continue;
      }
      try {
        const result = await sendPush(device, {
          kind: "review",
          batchId: id,
          title: "HD Careers · 20 jobs ready",
          body: "Your priority 10 and backup 10 are ready for review."
        });
        if (result.ok) {
          await markReceived(id, device.id);
          results.push({deviceId: device.id, state: "sent"});
        } else {
          if (result.status === 410 || result.reason === "Unregistered") await removeDevice(device.id);
          results.push({deviceId: device.id, state: "failed", reason: result.reason});
        }
      } catch {
        results.push({deviceId: device.id, state: "error"});
      }
    }
    return res.status(200).json({ok: true, batchId: id, results});
  } catch {
    return res.status(502).json({error: "Unable to dispatch the review notification."});
  } finally {
    if (lockedBatch) await unlockDispatch(lockedBatch).catch(() => {});
  }
}
