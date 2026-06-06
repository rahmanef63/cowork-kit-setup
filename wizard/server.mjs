#!/usr/bin/env node
// wizard/server.mjs — zero-dependency local GUI for creating Cowork project folders.
// Run:  node wizard/server.mjs   then open the printed URL.
// It serves an interview form and, on submit, runs the scaffolder to create
// projects/<slug>/. No npm install, no Convex — just Node + Python.

import http from "node:http";
import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve, join } from "node:path";
import { execFile } from "node:child_process";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");
const SCAFFOLD = join(ROOT, "skills", "cowork-automation-generator", "scripts", "scaffold.py");
const PROJECTS = join(ROOT, "projects");
const PORT = Number(process.env.PORT) || 4321;
const PYTHON = process.env.PYTHON || "python3";

function slugify(s) {
  return String(s).trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "automation";
}
function send(res, code, type, body) {
  res.writeHead(code, { "Content-Type": type });
  res.end(body);
}
function json(res, code, obj) {
  send(res, code, "application/json; charset=utf-8", JSON.stringify(obj));
}

function handleGenerate(res, data) {
  const field = String(data.field || "").trim();
  if (!field) return json(res, 400, { error: "Field/role is required." });
  const slug = slugify(field);
  const out = join(PROJECTS, slug);
  if (existsSync(out) && !data.force) {
    return json(res, 200, { needsConfirm: true, slug, message: `projects/${slug} already exists.` });
  }
  const surfaces = ["cowork"];
  if (data.cli !== false) surfaces.push("cli");
  if (data.web) surfaces.push("web");
  if (data.mcp) surfaces.push("mcp");

  const args = [SCAFFOLD, "--domain", field, "--surfaces", surfaces.join(","), "--out", out, "--force"];
  if (data.display) args.push("--display", String(data.display));
  if (data.description) args.push("--description", String(data.description));

  execFile(PYTHON, args, { cwd: ROOT, timeout: 60000 }, (err, stdout, stderr) => {
    if (err) {
      return json(res, 500, { error: (stderr || err.message || "scaffold failed").trim() });
    }
    json(res, 200, { ok: true, slug, out: `projects/${slug}`, surfaces, stdout: String(stdout).trim() });
  });
}

const server = http.createServer((req, res) => {
  if (req.method === "GET" && (req.url === "/" || req.url === "/index.html")) {
    try {
      return send(res, 200, "text/html; charset=utf-8", readFileSync(join(HERE, "index.html"), "utf-8"));
    } catch {
      return send(res, 500, "text/plain", "index.html not found next to server.mjs");
    }
  }
  if (req.method === "POST" && req.url === "/api/generate") {
    let body = "";
    req.on("data", (c) => { body += c; if (body.length > 1e6) req.destroy(); });
    req.on("end", () => {
      let data;
      try { data = JSON.parse(body || "{}"); } catch { return json(res, 400, { error: "bad JSON" }); }
      try { handleGenerate(res, data); } catch (e) { json(res, 500, { error: String(e && e.message || e) }); }
    });
    return;
  }
  send(res, 404, "text/plain", "not found");
});

server.listen(PORT, () => {
  console.log("\n  Cowork Project Wizard");
  console.log(`  → open http://localhost:${PORT}`);
  console.log(`  → creates folders in ${PROJECTS}\n`);
  if (!existsSync(SCAFFOLD)) {
    console.warn("  WARNING: scaffolder not found at", SCAFFOLD);
  }
});
