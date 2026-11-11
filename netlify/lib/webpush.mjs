// Minimal Web Push sender (RFC 8030 + RFC 8291 aes128gcm encryption + RFC 8292 VAPID), using only node:crypto.
// No third-party packages, so there is nothing to keep updated.
import crypto from "node:crypto";

const b64u = (buf) => Buffer.from(buf).toString("base64url");
const fromB64u = (s) => Buffer.from(s, "base64url");

/** A fresh VAPID key pair: { publicKey: base64url raw 65-byte point, privateJwk } */
export function makeVapidKeys() {
  const { publicKey, privateKey } = crypto.generateKeyPairSync("ec", { namedCurve: "prime256v1" });
  const jwk = privateKey.export({ format: "jwk" });
  const raw = publicKey.export({ format: "der", type: "spki" }).subarray(-65);
  return { publicKey: b64u(raw), privateJwk: jwk };
}

function vapidHeader(endpoint, keys, subject) {
  const aud = new URL(endpoint).origin;
  const head = b64u(JSON.stringify({ typ: "JWT", alg: "ES256" }));
  const body = b64u(JSON.stringify({ aud, exp: Math.floor(Date.now() / 1000) + 12 * 3600, sub: subject }));
  const key = crypto.createPrivateKey({ key: keys.privateJwk, format: "jwk" });
  const sig = crypto.sign("sha256", Buffer.from(`${head}.${body}`), { key, dsaEncoding: "ieee-p1363" });
  return `vapid t=${head}.${body}.${b64u(sig)}, k=${keys.publicKey}`;
}

const hmac = (key, data) => crypto.createHmac("sha256", key).update(data).digest();

/** Encrypt a payload for one subscription (aes128gcm, a single record). */
export function encrypt(payload, sub, { salt = crypto.randomBytes(16), ecdh = null } = {}) {
  const uaPublic = fromB64u(sub.keys.p256dh);
  const authSecret = fromB64u(sub.keys.auth);
  const as = ecdh || crypto.createECDH("prime256v1");
  if (!ecdh) as.generateKeys();
  const asPublic = as.getPublicKey();
  const shared = as.computeSecret(uaPublic);
  const prkKey = hmac(authSecret, shared);
  const ikm = hmac(prkKey, Buffer.concat([Buffer.from("WebPush: info\0"), uaPublic, asPublic, Buffer.from([1])]));
  const prk = hmac(salt, ikm);
  const cek = hmac(prk, Buffer.concat([Buffer.from("Content-Encoding: aes128gcm\0"), Buffer.from([1])])).subarray(0, 16);
  const nonce = hmac(prk, Buffer.concat([Buffer.from("Content-Encoding: nonce\0"), Buffer.from([1])])).subarray(0, 12);
  const cipher = crypto.createCipheriv("aes-128-gcm", cek, nonce);
  const ct = Buffer.concat([cipher.update(Buffer.concat([Buffer.from(payload), Buffer.from([2])])), cipher.final(), cipher.getAuthTag()]);
  const rs = Buffer.alloc(4); rs.writeUInt32BE(4096);
  return Buffer.concat([salt, rs, Buffer.from([asPublic.length]), asPublic, ct]);
}

/** Send one notification. Resolves to the push service's HTTP status (201 = accepted, 404/410 = subscription gone). */
export async function sendPush(sub, data, keys, { subject = "https://pitwallf1.in", ttl = 3600, urgency = "high", topic } = {}) {
  const body = encrypt(JSON.stringify(data), sub);
  const headers = {
    "Content-Encoding": "aes128gcm", "Content-Type": "application/octet-stream", TTL: String(ttl), Urgency: urgency,
    Authorization: vapidHeader(sub.endpoint, keys, subject),
  };
  if (topic) headers.Topic = topic.replace(/[^A-Za-z0-9_-]/g, "").slice(0, 32);
  const r = await fetch(sub.endpoint, { method: "POST", headers, body });
  return r.status;
}

// Push services browsers use. Subscriptions pointing anywhere else are refused (no open relay).
const PUSH_HOSTS = [/^fcm\.googleapis\.com$/, /^updates\.push\.services\.mozilla\.com$/, /^web\.push\.apple\.com$/, /\.notify\.windows\.com$/, /^push\.services\.mozilla\.com$/];
export function validSubscription(s) {
  try {
    const u = new URL(s.endpoint);
    return u.protocol === "https:" && PUSH_HOSTS.some((rx) => rx.test(u.hostname)) &&
      fromB64u(s.keys.p256dh).length === 65 && fromB64u(s.keys.auth).length === 16 && s.endpoint.length < 1000;
  } catch { return false; }
}

export const subKey = (endpoint) => "sub/" + crypto.createHash("sha256").update(endpoint).digest("hex").slice(0, 40);

/** The site's VAPID keys, created on first use and kept in the private Blobs store (nothing to configure). */
export async function getVapid(store) {
  let k = await store.get("vapid", { type: "json" });
  if (!k) { k = makeVapidKeys(); await store.setJSON("vapid", k); }
  return k;
}
