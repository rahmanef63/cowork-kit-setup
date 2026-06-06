<!-- Purpose: setup + architecture guide for the Next.js + Convex + BYOK webapp. -->

# Automation Webapp (Next.js + Convex + BYOK)

A browser front-end for the **same automation agent** as the Python CLI. The
difference: each user supplies **their own Anthropic API key** (BYOK) in the UI.
The key is stored per anonymous session in Convex and used at request time. There
is **no server-side Anthropic key** — never ship one with this template.

Both front-ends read the same contract, `automation.config.json` (at the repo
root). This app bundles its own copy at `web/automation.config.json` so the file
ships with the build and is importable from Convex server code. Keep the two in
sync (re-copy the root file, or re-run the generator).

## Setup

```bash
cd web
npm install

# 1) Provision a Convex deployment. This does two important things:
#    - generates the convex/_generated/ folder (api, server, dataModel types)
#    - writes NEXT_PUBLIC_CONVEX_URL into .env.local for you
npx convex dev      # leave running in one terminal

# 2) In a second terminal, start Next.js
npm run dev         # http://localhost:3000
```

> **Heads-up about `convex/_generated/`.** Several files import from
> `./_generated/server`, `./_generated/api`, and `./_generated/dataModel`
> (and `lib/tools.ts` / `app/page.tsx` import `../convex/_generated/...`). Those
> files **do not exist until you run `npx convex dev`**. Before the first run your
> editor will show "cannot find module" errors on those imports — that is
> expected. They resolve as soon as Convex generates the folder.

Scripts (`package.json`): `dev`, `build`, `start`, and `convex` (`convex dev`).

## BYOK flow

1. Open the app. An anonymous `sessionId` is generated and saved in
   `localStorage` (see `app/providers.tsx`).
2. Paste your Anthropic key (from console.anthropic.com) into the password field
   and click **Save**. It is stored in the `apiKeys` table keyed by your session
   (`convex/keys.ts` → `setKey`). The UI only ever reads `keyStatus`
   (`{ hasKey: boolean }`) — the key is **never** returned to the browser.
3. Enter a task (or pick a workflow from the dropdown) and click **Run**.
   `api.agent.runAgent` reads your key, starts a run, and streams progress.
4. Click **Clear** to delete your key at any time.

## How a run works

`runAgent` (in `convex/agent.ts`) validates the contract, checks your BYOK key,
creates a `runs` row, and **returns the `runId` immediately** while scheduling the
real work (`executeRun`). The UI subscribes with
`useQuery(api.store.getRun, { runId })`, so the transcript renders **live** as the
agent works.

`executeRun` runs the canonical Anthropic tool loop with `new Anthropic({ apiKey })`:

- `client.messages.stream(...)` — text deltas are flushed into the run's
  `transcript` (`appendAssistantDelta`) so you see tokens appear live.
- On `stop_reason === "tool_use"`, each tool call is dispatched against Convex
  (`lib/tools.ts` → `dispatchTool`), the call and result are appended to the
  transcript, results are fed back, and the loop continues.
- Otherwise the run is marked `done` (or `error`).

### The six tools (Convex-backed)

Same names/schemas as the Python CLI, but implemented against Convex tables
instead of local disk (the server has no access to your files):

| Tool                | Convex effect                                              |
| ------------------- | --------------------------------------------------------- |
| `read_document`     | read the latest `documents` row where `name == path`      |
| `list_workspace`    | list `documents` names (optional substring filter)        |
| `write_deliverable` | insert/replace a `documents` row                          |
| `save_record`       | insert a `records` row `{ table, data }`                  |
| `lookup_record`     | query `records` by table, substring-match the data JSON   |
| `create_task`       | insert a `tasks` row                                       |

`validateConfigTools(config)` throws at startup if the config references a handler
the dispatcher doesn't implement — this keeps the contract honest.

## Tables (`convex/schema.ts`)

- `apiKeys` — `{ sessionId, key, createdAt }`, indexed `by_session`.
- `documents` — `{ name, content, updatedAt }`, indexed `by_name`.
- `records` — `{ table, data, createdAt }`, indexed `by_table`.
- `tasks` — `{ title, due?, notes?, done, createdAt }`.
- `runs` — `{ sessionId, task, status, transcript[], createdAt, updatedAt }`,
  indexed `by_session`. `transcript` is an append-only array of events
  (`assistant`, `tool_call`, `tool_result`, `error`).

## Two streaming approaches

1. **DB-subscription (default).** A Convex `action` cannot stream over HTTP, so
   `executeRun` writes incremental events into the `runs` table and the client
   subscribes via `useQuery`. This is the path the UI uses and the one to prefer —
   it survives reloads (the run is in the DB) and needs no custom client.

2. **httpAction SSE (alternative).** `convex/http.ts` exposes
   `POST /stream-chat`, an `httpAction` that uses a `TransformStream` to stream
   raw Anthropic token deltas as Server-Sent Events. BYOK key comes from the POST
   body. It demonstrates true token streaming for a custom client; it streams a
   single assistant turn (no tool loop) to keep the example focused. Example:

   ```bash
   curl -N -X POST "$NEXT_PUBLIC_CONVEX_URL/stream-chat" \
     -H "Content-Type: application/json" \
     -d '{"apiKey":"sk-ant-...","task":"Say hello in one sentence."}'
   ```

   (The HTTP actions URL is your deployment's `.convex.site` origin; see the
   Convex dashboard.)

## Security note (read before deploying)

This template stores each user's Anthropic key **as plaintext** in the `apiKeys`
table, scoped to an anonymous session id. That is fine for local development and
demos, but for a real deployment you should:

- **Encrypt keys at rest** (e.g. envelope-encrypt with a KMS-managed key) and
  decrypt only inside the action at request time.
- **Scope and authenticate sessions** — replace the anonymous localStorage id
  with real auth so one user can't reach another's key or runs.
- **Consider not persisting the key at all** — accept it per request from the
  client and keep it only in memory for the duration of the run.
- Never log the key, never return it to the client, and never add a server-side
  `ANTHROPIC_API_KEY` to this app.
