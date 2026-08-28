import "dotenv/config";
import { betterAuth } from "better-auth";
import { bearer, emailOTP } from "better-auth/plugins";
import { Pool } from "pg";
import { Resend } from "resend";

const databaseUrl = process.env.DATABASE_URL?.trim();
if (!databaseUrl) {
  throw new Error("DATABASE_URL is required");
}

const secret = process.env.BETTER_AUTH_SECRET?.trim() || "";
if (secret.length < 32) {
  throw new Error("BETTER_AUTH_SECRET must be at least 32 characters");
}

const baseURL = (process.env.BETTER_AUTH_URL || "http://localhost:3000").replace(/\/$/, "");

const trustedOrigins = (
  process.env.TRUSTED_ORIGINS ||
  "http://localhost:1420,tauri://localhost,http://tauri.localhost"
)
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);

const resendKey = process.env.RESEND_API_KEY?.trim() || "";
const resend = resendKey ? new Resend(resendKey) : null;
const from = process.env.RESEND_FROM?.trim() || "Nous <noreply@localhost>";
const logOtp =
  process.env.AUTH_DEV_LOG_OTP !== "0" &&
  (process.env.AUTH_DEV_LOG_OTP === "1" || !resendKey);

export const pool = new Pool({ connectionString: databaseUrl });

export const auth = betterAuth({
  database: pool,
  secret,
  baseURL,
  trustedOrigins,
  plugins: [
    bearer(),
    emailOTP({
      otpLength: 6,
      expiresIn: 300,
      allowedAttempts: 3,
      disableSignUp: false,
      storeOTP: "hashed",
      async sendVerificationOTP({ email, otp, type }) {
        if (logOtp) {
          console.log(`[auth] OTP for ${email} (${type}): ${otp}`);
        }
        if (!resend) return;
        void resend.emails
          .send({
            from,
            to: email,
            subject: type === "sign-in" ? "Your Nous sign-in code" : "Your Nous code",
            text: `Your code is ${otp}. It expires in 5 minutes.`,
          })
          .catch((err) => console.error("[auth] Resend failed:", err));
      },
    }),
  ],
});
