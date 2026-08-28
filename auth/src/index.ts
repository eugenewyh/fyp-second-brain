import "dotenv/config";
import { serve } from "@hono/node-server";
import { Hono } from "hono";
import { cors } from "hono/cors";
import { auth, pool } from "./auth.js";

const port = Number(process.env.PORT || 3000);
const internalSecret = (process.env.AUTH_INTERNAL_SECRET || "").trim();

const trustedOrigins = (
  process.env.TRUSTED_ORIGINS ||
  "http://localhost:1420,tauri://localhost,http://tauri.localhost"
)
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);

const app = new Hono();

app.use(
  "*",
  cors({
    origin: (origin) => {
      if (!origin) return trustedOrigins[0] || "*";
      return trustedOrigins.includes(origin) ? origin : trustedOrigins[0] || origin;
    },
    credentials: true,
    allowHeaders: ["Content-Type", "Authorization", "X-Internal-Secret"],
    allowMethods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
  }),
);

app.get("/health", (c) =>
  c.json({ status: "ok", service: "nous-auth", version: "1.0.0" }),
);

app.on(["POST", "GET"], "/api/auth/*", (c) => auth.handler(c.req.raw));

/** Cloud Watch / sidecar: resolve Better Auth session → user. */
app.get("/internal/session", async (c) => {
  if (!internalSecret) {
    return c.json({ error: "AUTH_INTERNAL_SECRET not configured" }, 503);
  }
  const got = c.req.header("X-Internal-Secret") || "";
  if (got !== internalSecret) {
    return c.json({ error: "Unauthorized" }, 401);
  }
  const authHeader = c.req.header("Authorization") || "";
  if (!authHeader.toLowerCase().startsWith("bearer ")) {
    return c.json({ error: "Missing Bearer token" }, 401);
  }

  const headers = new Headers();
  headers.set("authorization", authHeader);
  const session = await auth.api.getSession({ headers });
  if (!session?.user) {
    return c.json({ error: "Invalid or expired session" }, 401);
  }
  return c.json({
    userId: session.user.id,
    email: session.user.email,
    name: session.user.name || "",
  });
});

app.post("/devices/register", async (c) => {
  const session = await auth.api.getSession({ headers: c.req.raw.headers });
  let userId = session?.user?.id;
  if (!userId) {
    const authHeader = c.req.header("Authorization") || "";
    const token = authHeader.toLowerCase().startsWith("bearer ")
      ? authHeader.slice(7).trim()
      : "";
    if (token) {
      const { rows } = await pool.query(
        `SELECT "userId" as user_id FROM session
         WHERE token = $1 AND "expiresAt" > now() LIMIT 1`,
        [token],
      );
      userId = rows[0]?.user_id;
    }
  }
  if (!userId) {
    return c.json({ error: "Unauthorized" }, 401);
  }

  const body = (await c.req.json().catch(() => ({}))) as {
    device_id?: string;
    public_key?: string;
    name?: string;
  };
  const deviceId = (body.device_id || "").trim();
  if (!deviceId) {
    return c.json({ error: "device_id required" }, 400);
  }
  const publicKey = (body.public_key || "").trim();
  const name = (body.name || "").trim().slice(0, 120);

  await pool.query(
    `
    INSERT INTO devices (id, user_id, device_id, public_key, name)
    VALUES (gen_random_uuid(), $1, $2, $3, $4)
    ON CONFLICT (device_id) DO UPDATE SET
      user_id = EXCLUDED.user_id,
      public_key = COALESCE(NULLIF(EXCLUDED.public_key, ''), devices.public_key),
      name = COALESCE(NULLIF(EXCLUDED.name, ''), devices.name)
    `,
    [userId, deviceId, publicKey, name],
  );

  return c.json({ ok: true, device_id: deviceId, user_id: userId });
});

app.get("/devices/me", async (c) => {
  const session = await auth.api.getSession({ headers: c.req.raw.headers });
  let userId = session?.user?.id;
  if (!userId) {
    const authHeader = c.req.header("Authorization") || "";
    const token = authHeader.toLowerCase().startsWith("bearer ")
      ? authHeader.slice(7).trim()
      : "";
    if (token) {
      const { rows } = await pool.query(
        `SELECT "userId" as user_id FROM session
         WHERE token = $1 AND "expiresAt" > now() LIMIT 1`,
        [token],
      );
      userId = rows[0]?.user_id;
    }
  }
  if (!userId) {
    return c.json({ error: "Unauthorized" }, 401);
  }
  const { rows } = await pool.query(
    `SELECT device_id, name, created_at FROM devices WHERE user_id = $1 ORDER BY created_at DESC`,
    [userId],
  );
  return c.json({ devices: rows });
});

serve({ fetch: app.fetch, port }, () => {
  console.log(`Nous auth listening on http://localhost:${port}`);
});
