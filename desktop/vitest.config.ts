import { defineConfig } from "vitest/config";
import { sveltekit } from "@sveltejs/kit/vite";
import path from "path";

export default defineConfig({
  plugins: [sveltekit()],
  resolve: {
    conditions: ["browser"],
    alias: {
      $lib: path.resolve(__dirname, "./src/lib"),
    },
  },
  test: {
    include: ["src/**/*.test.ts"],
    environment: "happy-dom",
  },
});