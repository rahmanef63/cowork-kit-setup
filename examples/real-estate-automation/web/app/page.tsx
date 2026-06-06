"use client";
// Purpose: the BYOK automation UI — key entry, task runner with a workflow
// dropdown, a live transcript subscribed from Convex, and document/task panels.

import { useState } from "react";
import { useAction, useMutation, useQuery } from "convex/react";
import { api } from "../convex/_generated/api";
import type { Id } from "../convex/_generated/dataModel";
import { config } from "../lib/config";
import { useSessionId } from "./providers";

/** A single transcript event. Fields are optional because the type varies. */
interface TEvent {
  type: string;
  text?: string;
  name?: string;
  input?: unknown;
  content?: string;
  message?: string;
}

export default function Page() {
  const sessionId = useSessionId();

  const keyStatus = useQuery(
    api.keys.keyStatus,
    sessionId ? { sessionId } : "skip",
  );
  const setKey = useMutation(api.keys.setKey);
  const clearKey = useMutation(api.keys.clearKey);
  const runAgent = useAction(api.agent.runAgent);

  const documents = useQuery(api.store.listAllDocuments, {});
  const tasks = useQuery(api.store.listAllTasks, {});

  const [keyInput, setKeyInput] = useState("");
  const [task, setTask] = useState("");
  const [workflow, setWorkflow] = useState("");
  const [runId, setRunId] = useState<Id<"runs"> | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Subscribes live: every transcript append re-renders this component.
  const run = useQuery(api.store.getRun, runId ? { runId } : "skip");
  const transcript: TEvent[] = (run?.transcript ?? []) as TEvent[];
  const hasKey = keyStatus?.hasKey ?? false;
  const running = run?.status === "running";

  async function handleSaveKey() {
    if (!keyInput.trim() || !sessionId) return;
    await setKey({ sessionId, key: keyInput.trim() });
    setKeyInput("");
  }

  async function handleClearKey() {
    if (!sessionId) return;
    await clearKey({ sessionId });
  }

  function handleWorkflow(name: string) {
    setWorkflow(name);
    const wf = config.workflows.find((w) => w.name === name);
    if (wf) setTask(wf.prompt);
  }

  async function handleRun() {
    setError(null);
    if (!sessionId) return;
    if (!task.trim()) {
      setError("Enter a task first.");
      return;
    }
    if (!hasKey) {
      setError("Save your Anthropic API key first.");
      return;
    }
    setStarting(true);
    try {
      const id = await runAgent({
        sessionId,
        task: task.trim(),
        model: config.model,
      });
      setRunId(id);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setStarting(false);
    }
  }

  return (
    <main className="page">
      <header className="page-header">
        <h1>{config.displayName}</h1>
        <p>{config.description}</p>
      </header>

      <div className="grid">
        <div className="stack">
          {/* BYOK key */}
          <section className="card">
            <h2>Anthropic API key (BYOK)</h2>
            <div className="row" style={{ marginBottom: 8 }}>
              <span className="pill">
                <span className={`dot ${hasKey ? "good" : "bad"}`} />
                {keyStatus === undefined
                  ? "checking…"
                  : hasKey
                    ? "key stored"
                    : "no key"}
              </span>
            </div>
            <label htmlFor="key">
              Paste your key — stored per session in Convex, never shown back.
            </label>
            <div className="row">
              <input
                id="key"
                type="password"
                placeholder="sk-ant-..."
                value={keyInput}
                autoComplete="off"
                onChange={(e) => setKeyInput(e.target.value)}
              />
              <button onClick={handleSaveKey} disabled={!keyInput.trim()}>
                Save
              </button>
              <button
                className="secondary"
                onClick={handleClearKey}
                disabled={!hasKey}
              >
                Clear
              </button>
            </div>
            <p className="hint">
              Get a key at console.anthropic.com. It is sent to Convex and used
              only to call Anthropic on your behalf.
            </p>
          </section>

          {/* Task runner */}
          <section className="card">
            <h2>Run a task</h2>
            <label htmlFor="wf">Start from a workflow (optional)</label>
            <select
              id="wf"
              value={workflow}
              onChange={(e) => handleWorkflow(e.target.value)}
            >
              <option value="">— custom task —</option>
              {config.workflows.map((w) => (
                <option key={w.name} value={w.name}>
                  {w.name} — {w.description}
                </option>
              ))}
            </select>

            <label htmlFor="task" style={{ marginTop: 12 }}>
              Task
            </label>
            <textarea
              id="task"
              value={task}
              placeholder="Describe what you want the agent to do…"
              onChange={(e) => setTask(e.target.value)}
            />

            <div className="row" style={{ marginTop: 10 }}>
              <button onClick={handleRun} disabled={starting || running}>
                {starting ? "Starting…" : running ? "Running…" : "Run"}
              </button>
              <span className="hint">
                model: <code>{config.model}</code>
              </span>
            </div>
            {error && (
              <p className="error" style={{ marginTop: 8 }}>
                {error}
              </p>
            )}
          </section>

          {/* Live transcript */}
          <section className="card">
            <h2>
              Transcript
              {run && (
                <span className="pill" style={{ marginLeft: 8 }}>
                  <span
                    className={`dot ${
                      run.status === "done"
                        ? "good"
                        : run.status === "error"
                          ? "bad"
                          : "run"
                    }`}
                  />
                  {run.status}
                </span>
              )}
            </h2>
            <div className="transcript">
              {!run && (
                <div className="empty">
                  Run a task to see the live transcript.
                </div>
              )}
              {run && transcript.length === 0 && (
                <div className="empty">Waiting for the agent…</div>
              )}
              {transcript.map((ev, i) => (
                <TranscriptItem key={i} ev={ev} />
              ))}
            </div>
          </section>
        </div>

        {/* Side panel: what the agent produced */}
        <div className="stack">
          <section className="card">
            <h2>Documents</h2>
            {documents === undefined && <div className="empty">Loading…</div>}
            {documents && documents.length === 0 && (
              <div className="empty">No deliverables yet.</div>
            )}
            <ul className="list">
              {documents?.map((d) => (
                <li key={d._id}>
                  <div>{d.name}</div>
                  <div className="meta">
                    {d.chars} chars · {new Date(d.updatedAt).toLocaleString()}
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section className="card">
            <h2>Tasks</h2>
            {tasks === undefined && <div className="empty">Loading…</div>}
            {tasks && tasks.length === 0 && (
              <div className="empty">No tasks yet.</div>
            )}
            <ul className="list">
              {tasks?.map((t) => (
                <li key={t._id}>
                  <div>{t.title}</div>
                  <div className="meta">
                    {t.due ? `due ${t.due} · ` : ""}
                    {new Date(t.createdAt).toLocaleString()}
                  </div>
                  {t.notes && <div className="meta">{t.notes}</div>}
                </li>
              ))}
            </ul>
          </section>
        </div>
      </div>
    </main>
  );
}

/** Render one transcript event, styled by type. */
function TranscriptItem({ ev }: { ev: TEvent }) {
  if (ev.type === "assistant") {
    return (
      <div className="event assistant">
        <div className="label">assistant</div>
        {ev.text ? ev.text : <span className="empty">…</span>}
      </div>
    );
  }
  if (ev.type === "tool_call") {
    return (
      <div className="event tool">
        <div className="label">
          tool call · <span className="name">{ev.name}</span>
        </div>
        <pre>{JSON.stringify(ev.input ?? {}, null, 2)}</pre>
      </div>
    );
  }
  if (ev.type === "tool_result") {
    return (
      <div className="event tool">
        <div className="label">
          tool result · <span className="name">{ev.name}</span>
        </div>
        <pre>{ev.content ?? ""}</pre>
      </div>
    );
  }
  if (ev.type === "error") {
    return (
      <div className="event">
        <div className="label">error</div>
        <pre className="error">{ev.message ?? "unknown error"}</pre>
      </div>
    );
  }
  return (
    <div className="event">
      <div className="label">{ev.type}</div>
      <pre>{JSON.stringify(ev, null, 2)}</pre>
    </div>
  );
}
