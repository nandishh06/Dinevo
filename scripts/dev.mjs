#!/usr/bin/env node
// Local dev runner: starts the FastAPI backend (:8000) and the Vite/TanStack
// frontend (:3000) together.
//
// - Backend: uvicorn loads backend/.env itself via --env-file (dotenv is part of
//   uvicorn[standard]) and runs with cwd = backend/ so `app.main:app` resolves.
// - Frontend: Vite reads the root .env for VITE_* vars.
// Secrets from backend/.env are passed only to the uvicorn process; they are
// never injected into the frontend process.
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const backendDir = resolve(root, "backend");
const uvicornBin = resolve(backendDir, ".venv/bin/uvicorn");
const viteBin = resolve(root, "node_modules/.bin/vite");

if (!existsSync(uvicornBin)) {
  console.error(`[dev] Backend virtualenv not found at ${uvicornBin}.`);
  console.error("[dev] Create it first: cd backend && python3.12 -m venv .venv && .venv/bin/pip install -e '.[dev]'");
  process.exit(1);
}

const children = [];
let shuttingDown = false;

function shutdown(code) {
  if (shuttingDown) return;
  shuttingDown = true;
  for (const child of children) {
    try {
      child.kill("SIGTERM");
    } catch {
      /* ignore */
    }
  }
  setTimeout(() => process.exit(code), 300);
}

function start(name, command, args, cwd, env) {
  const child = spawn(command, args, { cwd, env, stdio: "inherit" });
  child.on("error", (error) => {
    console.error(`[dev] ${name} failed to start: ${error.message}`);
    shutdown(1);
  });
  child.on("exit", (code, signal) => {
    if (shuttingDown) return;
    console.error(`[dev] ${name} exited (${signal ?? code}); stopping.`);
    shutdown(code ?? 0);
  });
  children.push(child);
}

process.on("SIGINT", () => shutdown(0));
process.on("SIGTERM", () => shutdown(0));

// Backend on :8000, env from backend/.env (never exposed to the frontend).
start(
  "api",
  uvicornBin,
  ["app.main:app", "--reload", "--port", "8000", "--env-file", ".env"],
  backendDir,
  process.env,
);

// Frontend on :3000 (Vite/TanStack; reads root .env).
start("web", viteBin, ["dev"], root, process.env);
