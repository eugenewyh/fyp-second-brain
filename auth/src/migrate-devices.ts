import "dotenv/config";
import { pool } from "./auth.js";

async function main() {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS devices (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id TEXT NOT NULL,
      device_id TEXT NOT NULL UNIQUE,
      public_key TEXT NOT NULL DEFAULT '',
      name TEXT NOT NULL DEFAULT '',
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE INDEX IF NOT EXISTS devices_user_id_idx ON devices (user_id);
  `);
  console.log("devices table ready");
  await pool.end();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
