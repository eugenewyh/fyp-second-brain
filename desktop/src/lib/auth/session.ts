/** Local persistence for Better Auth session + stable device id. */

const SESSION_KEY = "nous.auth.sessionToken";
const EMAIL_KEY = "nous.auth.email";
const DEVICE_KEY = "nous.auth.deviceId";
const DEVICE_NAME_KEY = "nous.auth.deviceName";

function storage(): Storage | null {
  try {
    return typeof localStorage !== "undefined" ? localStorage : null;
  } catch {
    return null;
  }
}

export function getSessionToken(): string {
  return storage()?.getItem(SESSION_KEY)?.trim() || "";
}

export function setSessionToken(token: string | null): void {
  const s = storage();
  if (!s) return;
  const t = (token || "").trim();
  if (t) s.setItem(SESSION_KEY, t);
  else s.removeItem(SESSION_KEY);
}

export function getStoredEmail(): string {
  return storage()?.getItem(EMAIL_KEY)?.trim() || "";
}

export function setStoredEmail(email: string | null): void {
  const s = storage();
  if (!s) return;
  const e = (email || "").trim();
  if (e) s.setItem(EMAIL_KEY, e);
  else s.removeItem(EMAIL_KEY);
}

export function getOrCreateDeviceId(): string {
  const s = storage();
  const existing = s?.getItem(DEVICE_KEY)?.trim();
  if (existing) return existing;
  const id =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `dev-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  s?.setItem(DEVICE_KEY, id);
  return id;
}

export function getDeviceName(): string {
  const s = storage();
  const existing = s?.getItem(DEVICE_NAME_KEY)?.trim();
  if (existing) return existing;
  const name =
    typeof navigator !== "undefined" && navigator.platform
      ? `Mac (${navigator.platform})`
      : "This Mac";
  s?.setItem(DEVICE_NAME_KEY, name);
  return name;
}

export function clearAuthLocal(): void {
  setSessionToken(null);
  setStoredEmail(null);
}
