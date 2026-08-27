/** Reactive Account session — localStorage alone does not update the Sidebar. */

import {
  clearAuthLocal,
  getSessionToken,
  getStoredEmail,
  setSessionToken as persistToken,
  setStoredEmail as persistEmail,
} from "./session";

class AuthStore {
  token = $state("");
  email = $state("");
  name = $state("");
  hydrated = $state(false);

  get signedIn(): boolean {
    return Boolean(this.token.trim());
  }

  /** Prefer display name, then email local-part, then full email. */
  get label(): string {
    const name = this.name.trim();
    if (name) return name;
    const email = this.email.trim();
    if (!email) return this.signedIn ? "Signed in" : "Sign in";
    const local = email.split("@")[0]?.trim();
    return local || email;
  }

  get initial(): string {
    const src = this.name.trim() || this.email.trim();
    return (src[0] || "?").toUpperCase();
  }

  hydrate() {
    this.token = getSessionToken();
    this.email = getStoredEmail();
    this.hydrated = true;
  }

  setSession(opts: { token: string; email?: string; name?: string }) {
    const token = opts.token.trim();
    persistToken(token || null);
    this.token = token;
    if (opts.email !== undefined) {
      const email = opts.email.trim().toLowerCase();
      persistEmail(email || null);
      this.email = email;
    }
    if (opts.name !== undefined) {
      this.name = opts.name.trim();
    }
  }

  setProfile(opts: { email?: string; name?: string }) {
    if (opts.email !== undefined) {
      const email = opts.email.trim().toLowerCase();
      persistEmail(email || null);
      this.email = email;
    }
    if (opts.name !== undefined) {
      this.name = opts.name.trim();
    }
  }

  clear() {
    clearAuthLocal();
    this.token = "";
    this.email = "";
    this.name = "";
  }
}

export const authSession = new AuthStore();
