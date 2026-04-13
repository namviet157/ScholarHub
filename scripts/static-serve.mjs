/**
 * Production static server for Railway / Docker (reads PORT).
 * Uses `serve` from dependencies so runtime does not need Vite.
 */
import { spawn } from "node:child_process";
import process from "node:process";

const port = process.env.PORT || "3000";
const child = spawn(
  "npx",
  ["serve", "dist", "-s", "-l", `tcp://0.0.0.0:${port}`],
  { stdio: "inherit", shell: true, cwd: process.cwd() },
);
child.on("exit", (code) => process.exit(code ?? 0));
