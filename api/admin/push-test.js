import {requireAdmin} from "../../lib/admin-auth.js";
import {devices, pushStorageConfigured, removeDevice} from "../../lib/push-redis.js";
import {apnsConfigured, sendPush} from "../../lib/apns-client.js";

function sameOrigin(req) {
  const origin = String(req.headers.origin || "");
  if (!origin) return true;
  const host = String(req.headers["x-forwarded-host"] || req.headers.host || "").toLowerCase();
  try { return new URL(origin).host.toLowerCase() === host; } catch { return false; }
}

export default async function handler(req, res) {
  res.setHeader("Cache-Control", "private, no-store");
  if (req.method !== "POST") return res.status(405).json({error: "Method not allowed"});
  if (!requireAdmin(req, res)) return;
  if (!sameOrigin(req)) return res.status(403).json({error: "Invalid request origin"});
  if (!pushStorageConfigured() || !apnsConfigured()) return res.status(503).json({error: "Apple push delivery has not been configured."});
  try {
    const registered = await devices();
    if (!registered.length) return res.status(409).json({error: "No iPhone has registered for push notifications yet."});
    const results = [];
    for (const device of registered) {
      try {
        const result = await sendPush(device, {
          kind: "test",
          title: "HD Careers Push Test",
          body: "Your private Admin notification connection is working."
        });
        if (result.status === 410 || result.reason === "BadDeviceToken" || result.reason === "Unregistered") await removeDevice(device.id);
        results.push({deviceId: device.id, delivered: result.ok, reason: result.reason || null});
      } catch { results.push({deviceId: device.id, delivered: false, reason: "APNs connection failed"}); }
    }
    return res.status(200).json({ok: results.some(x => x.delivered), results});
  } catch {
    return res.status(502).json({error: "Could not complete the Apple push delivery test."});
  }
}
