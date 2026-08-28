import { createAuthClient } from "better-auth/client";
import { emailOTPClient } from "better-auth/client/plugins";
import { authSession } from "./auth-session.svelte";
import {
  getDeviceName,
  getOrCreateDeviceId,
  getSessionToken,
} from "./session";

const baseURL = (import.meta.env.VITE_AUTH_URL as string | undefined)?.replace(/\/$/, "") || "";

export function authConfigured(): boolean {
  return Boolean(baseURL);
}

export const authClient = createAuthClient({
  baseURL: baseURL || "http://localhost:3000",
  plugins: [emailOTPClient()],
});

function tokenFromCookie(): string {
  try {
    const match = document.cookie.match(/(?:^|;\s*)better-auth\.session_token=([^;]+)/);
    return match?.[1] ? decodeURIComponent(match[1]) : "";
  } catch {
    return "";
  }
}

export async function sendCode(email: string) {
  if (!authConfigured()) {
    return { error: { message: "Auth URL not configured (VITE_AUTH_URL)" } };
  }
  return authClient.emailOtp.sendVerificationOtp({
    email: email.trim().toLowerCase(),
    type: "sign-in",
  });
}

export async function verifyCode(email: string, otp: string, name?: string) {
  if (!authConfigured()) {
    return { error: { message: "Auth URL not configured (VITE_AUTH_URL)" } };
  }
  const normalized = email.trim().toLowerCase();
  const result = await authClient.signIn.emailOtp({
    email: normalized,
    otp: otp.trim(),
    ...(name?.trim() ? { name: name.trim() } : {}),
  });
  if (result.error) return result;

  const data = result.data as {
    token?: string;
    user?: { email?: string; name?: string };
    session?: { token?: string };
  } | null;

  let sessionToken =
    data?.token || data?.session?.token || tokenFromCookie() || "";

  if (!sessionToken) {
    const sess = await authClient.getSession();
    sessionToken = sess.data?.session?.token || tokenFromCookie() || "";
    const u = sess.data?.user;
    authSession.setSession({
      token: sessionToken,
      email: u?.email || normalized,
      name: u?.name || name?.trim() || "",
    });
  } else {
    authSession.setSession({
      token: sessionToken,
      email: data?.user?.email || normalized,
      name: data?.user?.name || name?.trim() || "",
    });
  }

  await registerDevice().catch(() => {});
  return result;
}

export async function currentUser() {
  if (!getSessionToken() && !authConfigured()) {
    return { data: null, error: null };
  }
  const sess = await authClient.getSession({
    fetchOptions: {
      headers: getSessionToken()
        ? { Authorization: `Bearer ${getSessionToken()}` }
        : undefined,
    },
  });
  if (sess.data?.user) {
    authSession.setProfile({
      email: sess.data.user.email || "",
      name: sess.data.user.name || "",
    });
    if (sess.data.session?.token) {
      authSession.setSession({
        token: sess.data.session.token,
        email: sess.data.user.email || authSession.email,
        name: sess.data.user.name || authSession.name,
      });
    }
  }
  return sess;
}

export async function signOut() {
  try {
    await authClient.signOut({
      fetchOptions: {
        headers: getSessionToken()
          ? { Authorization: `Bearer ${getSessionToken()}` }
          : undefined,
      },
    });
  } catch {
    /* ignore */
  }
  authSession.clear();
}

export async function deleteAccount() {
  const client = authClient as {
    deleteUser?: (opts?: unknown) => Promise<unknown>;
    signOut: typeof authClient.signOut;
  };
  try {
    if (typeof client.deleteUser === "function") {
      await client.deleteUser({
        fetchOptions: {
          headers: getSessionToken()
            ? { Authorization: `Bearer ${getSessionToken()}` }
            : undefined,
        },
      });
    } else {
      await signOut();
      return { ok: true, note: "Signed out. Account deletion is not enabled on the server yet." };
    }
  } catch (e) {
    await signOut();
    throw e;
  }
  authSession.clear();
  return { ok: true };
}

async function registerDevice() {
  if (!baseURL || !getSessionToken()) return;
  const res = await fetch(`${baseURL}/devices/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getSessionToken()}`,
    },
    body: JSON.stringify({
      device_id: getOrCreateDeviceId(),
      name: getDeviceName(),
      public_key: "",
    }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `Device register failed (${res.status})`);
  }
}

export function formatAuthClientError(err: unknown, fallback: string): string {
  if (!err) return fallback;
  if (typeof err === "string") return err;
  if (typeof err === "object" && err !== null) {
    const o = err as { message?: string; error?: { message?: string } };
    if (o.error?.message) return o.error.message;
    if (o.message) return o.message;
  }
  return fallback;
}
