import crypto from "node:crypto";
import http2 from "node:http2";

const TOPIC = "in.hdcareers.admin";

export function apnsConfigured() {
  return Boolean(process.env.APNS_KEY_ID && process.env.APNS_TEAM_ID && process.env.APNS_PRIVATE_KEY_P8);
}

export function signedJwt() {
  const header = Buffer.from(JSON.stringify({alg: "ES256", kid: process.env.APNS_KEY_ID})).toString("base64url");
  const claims = Buffer.from(JSON.stringify({iss: process.env.APNS_TEAM_ID, iat: Math.floor(Date.now() / 1000)})).toString("base64url");
  const signingInput = header + "." + claims;
  const pem = process.env.APNS_PRIVATE_KEY_P8.replace(/\\n/g, "\n");
  const signature = crypto.sign("sha256", Buffer.from(signingInput), {
    key: crypto.createPrivateKey(pem),
    dsaEncoding: "ieee-p1363"
  }).toString("base64url");
  return signingInput + "." + signature;
}

export async function sendPush(device, alert) {
  if (!apnsConfigured()) throw new Error("Apple push credentials are not configured.");
  const env = device.environment === "production" ? "production" : "development";
  const host = env === "production" ? "https://api.push.apple.com" : "https://api.sandbox.push.apple.com";
  const payload = JSON.stringify({
    aps: {alert: {title: alert.title, body: alert.body}, sound: "default"},
    kind: alert.kind || "review",
    batchId: alert.batchId || ""
  });
  const jwt = signedJwt();

  return new Promise((resolve, reject) => {
    const connection = http2.connect(host);
    const timeout = setTimeout(() => {
      connection.destroy();
      reject(new Error("Apple push request timed out."));
    }, 9000);
    let complete = false;
    const finish = (error, value) => {
      if (complete) return;
      complete = true;
      clearTimeout(timeout);
      connection.close();
      if (error) reject(error); else resolve(value);
    };
    connection.on("error", error => finish(error));
    const request = connection.request({
      ":method": "POST",
      ":path": "/3/device/" + device.token,
      "authorization": "bearer " + jwt,
      "apns-topic": TOPIC,
      "apns-push-type": "alert",
      "apns-priority": "10",
      "content-type": "application/json"
    });
    let status = 0;
    let response = "";
    request.on("response", headers => { status = Number(headers[":status"] || 0); });
    request.on("data", data => { if (response.length < 1500) response += data; });
    request.on("error", error => finish(error));
    request.on("end", () => {
      let reason = "";
      try { reason = JSON.parse(response).reason || ""; } catch {}
      finish(null, {ok: status === 200, status, reason});
    });
    request.end(payload);
  });
}
