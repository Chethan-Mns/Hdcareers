const PREFIX = "hdcareers:apns:";

export function pushStorageConfigured() {
  return Boolean(process.env.UPSTASH_REDIS_REST_URL && process.env.UPSTASH_REDIS_REST_TOKEN);
}

export async function redis(command) {
  const url = process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.UPSTASH_REDIS_REST_TOKEN;
  if (!url || !token) throw new Error("Push device storage is not configured.");
  const response = await fetch(url.replace(/\/$/, ""), {
    method: "POST",
    headers: {"Authorization": "Bearer " + token, "Content-Type": "application/json"},
    body: JSON.stringify(command),
    cache: "no-store",
    signal: AbortSignal.timeout(6500)
  });
  if (!response.ok) throw new Error("Push device storage returned HTTP " + response.status);
  const payload = await response.json();
  if (payload.error) throw new Error("Push device storage operation failed.");
  return payload.result;
}

export const deviceKey = PREFIX + "devices";

export async function devices() {
  const result = await redis(["HGETALL", deviceKey]);
  if (!result) return [];
  const pairs = Array.isArray(result)
    ? Array.from({length: Math.floor(result.length / 2)}, (_, i) => [result[i * 2], result[i * 2 + 1]])
    : Object.entries(result);
  return pairs.map(([id, raw]) => {
    try { return {id, ...JSON.parse(raw)}; } catch { return null; }
  }).filter(Boolean);
}

export async function saveDevice(id, device) {
  return redis(["HSET", deviceKey, id, JSON.stringify(device)]);
}

export async function removeDevice(id) {
  return redis(["HDEL", deviceKey, id]);
}

export async function received(batchId, id) {
  return Boolean(await redis(["GET", PREFIX + "sent:" + batchId + ":" + id]));
}

export async function markReceived(batchId, id) {
  return redis(["SET", PREFIX + "sent:" + batchId + ":" + id, "1", "EX", 60 * 60 * 24 * 30]);
}

export async function lockDispatch(batchId) {
  return await redis(["SET", PREFIX + "lock:" + batchId, "1", "NX", "EX", 90]) === "OK";
}

export async function unlockDispatch(batchId) {
  return redis(["DEL", PREFIX + "lock:" + batchId]);
}
