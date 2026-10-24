import {requireAdmin} from "../../lib/admin-auth.js";
import {devices, saveDevice, removeDevice, pushStorageConfigured} from "../../lib/push-redis.js";
import {apnsConfigured} from "../../lib/apns-client.js";

function sameOrigin(req) {
  const origin = String(req.headers.origin || "");
  if (!origin) return true;
  const host = String(req.headers["x-forwarded-host"] || req.headers.host || "").toLowerCase();
  try { return new URL(origin).host.toLowerCase() === host; } catch { return false; }
}

export default async function handler(req, res) {
  res.setHeader("Cache-Control", "private, no-store");
  if (!["GET", "POST"].includes(req.method)) return res.status(405).json({error: "Method not allowed"});
  if (!requireAdmin(req, res)) return;
  if (!sameOrigin(req)) return res.status(403).json({error: "Invalid request origin"});
  const configured = pushStorageConfigured() && apnsConfigured();
  if (req.method === "GET") return res.status(200).json({configured, storageConfigured: pushStorageConfigured(), apnsConfigured: apnsConfigured()});
  if (!pushStorageConfigured()) return res.status(503).json({error: "Push storage is not configured."});

  const body = req.body || {};
  const id = String(body.installationId || "").trim();
  if (!/^[a-zA-Z0-9-]{20,64}$/.test(id)) return res.status(400).json({error: "Invalid device identifier."});
  try {
    if (body.action === "unregister") {
      await removeDevice(id);
      return res.status(200).json({ok: true, registered: false});
    }
    if (body.action !== "register") return res.status(400).json({error: "Invalid action."});
    if (!apnsConfigured()) return res.status(503).json({error: "APNs credentials have not been configured."});
    const token = String(body.token || "").toLowerCase().trim();
    const environment = body.environment === "production" ? "production" : body.environment === "development" ? "development" : null;
    if (!/^[0-9a-f]{32,256}$/.test(token) || !environment) return res.status(400).json({error: "Invalid APNs token or environment."});
    const existing = await devices();
    if (existing.length >= 8 && !existing.some(x => x.id === id)) return res.status(429).json({error: "Maximum 8 registered devices reached."});
    await saveDevice(id, {token, environment, updatedAt: new Date().toISOString()});
    return res.status(200).json({ok: true, registered: true});
  } catch {
    return res.status(502).json({error: "Unable to save the device registration."});
  }
}
