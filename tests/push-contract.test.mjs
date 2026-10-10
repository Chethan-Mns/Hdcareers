import test from "node:test";
import assert from "node:assert/strict";
import crypto from "node:crypto";
import {signedJwt, apnsConfigured} from "../lib/apns-client.js";
import {devices, pushStorageConfigured, saveDevice, redis} from "../lib/push-redis.js";
import deviceHandler from "../api/admin/push-devices.js";
import dispatchHandler from "../api/notifications/dispatch.js";

function response() {
  return {
    code: 200,
    body: null,
    setHeader() { return this; },
    status(code) { this.code = code; return this; },
    json(body) { this.body = body; return this; }
  };
}

test("server refuses to claim configured before private credentials exist", () => {
  assert.equal(pushStorageConfigured(), false);
  assert.equal(apnsConfigured(), false);
});

test("APNs provider token is signed and verified with ES256", () => {
  const {privateKey, publicKey} = crypto.generateKeyPairSync("ec", {namedCurve: "P-256"});
  const original = [process.env.APNS_PRIVATE_KEY_P8, process.env.APNS_KEY_ID, process.env.APNS_TEAM_ID];
  try {
    process.env.APNS_PRIVATE_KEY_P8 = privateKey.export({format: "pem", type: "pkcs8"}).toString();
    process.env.APNS_KEY_ID = "TESTKEY123";
    process.env.APNS_TEAM_ID = "TESTTEAM12";
    const jwt = signedJwt();
    const [encodedHeader, encodedClaims, encodedSignature] = jwt.split(".");
    const header = JSON.parse(Buffer.from(encodedHeader, "base64url").toString());
    const claims = JSON.parse(Buffer.from(encodedClaims, "base64url").toString());
    assert.equal(header.alg, "ES256");
    assert.equal(header.kid, "TESTKEY123");
    assert.equal(claims.iss, "TESTTEAM12");
    assert.ok(Math.abs(Math.floor(Date.now() / 1000) - claims.iat) < 5);
    assert.equal(crypto.verify("sha256", Buffer.from(encodedHeader + "." + encodedClaims),
      {key: publicKey, dsaEncoding: "ieee-p1363"}, Buffer.from(encodedSignature, "base64url")), true);
  } finally {
    [process.env.APNS_PRIVATE_KEY_P8, process.env.APNS_KEY_ID, process.env.APNS_TEAM_ID] =
      original.map(x => x === undefined ? undefined : x);
  }
});

test("Redis device registration uses authenticated private REST API", async () => {
  const previousUrl = process.env.UPSTASH_REDIS_REST_URL;
  const previousToken = process.env.UPSTASH_REDIS_REST_TOKEN;
  const originalFetch = globalThis.fetch;
  const commands = [];
  process.env.UPSTASH_REDIS_REST_URL = "https://unit-test.upstash.io";
  process.env.UPSTASH_REDIS_REST_TOKEN = "test-server-only-secret";
  globalThis.fetch = async (_url, options) => {
    assert.equal(options.headers.Authorization, "Bearer test-server-only-secret");
    commands.push(JSON.parse(options.body));
    return {ok: true, json: async () => ({result: commands.at(-1)[0] === "HGETALL" ? [
      "abc", JSON.stringify({token: "a".repeat(64), environment: "development"})
    ] : 1})};
  };
  try {
    assert.equal(pushStorageConfigured(), true);
    await saveDevice("abc", {token: "a".repeat(64), environment: "development"});
    assert.equal(commands[0][0], "HSET");
    const result = await devices();
    assert.equal(result[0].id, "abc");
    assert.equal(result[0].token, "a".repeat(64));
    assert.equal(commands[1][0], "HGETALL");
  } finally {
    globalThis.fetch = originalFetch;
    if (previousUrl === undefined) delete process.env.UPSTASH_REDIS_REST_URL;
    else process.env.UPSTASH_REDIS_REST_URL = previousUrl;
    if (previousToken === undefined) delete process.env.UPSTASH_REDIS_REST_TOKEN;
    else process.env.UPSTASH_REDIS_REST_TOKEN = previousToken;
  }
});

test("device registration rejects requests without admin authentication", async () => {
  const res = response();
  await deviceHandler({method: "POST", headers: {}, body: {action: "register"}}, res);
  assert.equal(res.code, 401);
});

test("batch-ready dispatch refuses requests without a secret", async () => {
  const res = response();
  await dispatchHandler({method: "POST", headers: {}}, res);
  assert.equal(res.code, 401);
});

test("invalid notification methods cannot dispatch", async () => {
  const res = response();
  await dispatchHandler({method: "GET", headers: {}}, res);
  assert.equal(res.code, 405);
});
