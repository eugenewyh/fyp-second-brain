import { execSync } from "child_process";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const scratch = process.env.SCRATCH_DIR ?? root;

process.chdir(root);

console.log("=== npm test ===");
const testOut = execSync("npm test", { encoding: "utf8" });
console.log(testOut);

console.log("=== npm run check ===");
const checkOut = execSync("npm run check", { encoding: "utf8" });
console.log(checkOut);

console.log("=== npm run build ===");
const buildOut = execSync("npm run build", { encoding: "utf8" });
console.log(buildOut);

const { writeFileSync } = await import("fs");
writeFileSync(resolve(scratch, "logic-exercise.log"), testOut + checkOut + buildOut);
console.log("logic-exercise complete");