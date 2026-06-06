// Purpose: load and strongly type the shared `automation.config.json` contract.
//
// This is the SAME contract the Python CLI reads. The webapp bundles its own copy
// (web/automation.config.json) so the file ships with the Next.js build and is also
// importable from Convex server code. Keep it in sync with the repo-root config.

import rawConfig from "../automation.config.json";

/** A JSON Schema fragment, as accepted by the Anthropic `input_schema` field. */
export interface JsonSchema {
  type: string;
  properties?: Record<string, JsonSchema | Record<string, unknown>>;
  items?: JsonSchema | Record<string, unknown>;
  required?: string[];
  description?: string;
  [key: string]: unknown;
}

/** One tool definition. `name` and `handler` are snake_case and identical to the Python side. */
export interface ToolSpec {
  name: string;
  description: string;
  handler: string;
  input_schema: JsonSchema;
}

/** A higher-level recipe surfaced in the workflow dropdown. */
export interface WorkflowSpec {
  name: string;
  description: string;
  prompt: string;
  schedule: string | null;
}

/** Domain-tuned guidance, shown in docs/README. */
export interface BestPractice {
  title: string;
  detail: string;
}

/** The full automation contract. */
export interface AutomationConfig {
  domain: string;
  displayName: string;
  description: string;
  version: string;
  model: string;
  systemPrompt: string;
  coworkCapabilities?: string[];
  suggestedConnectors?: string[];
  bestPractices?: BestPractice[];
  tools: ToolSpec[];
  workflows: WorkflowSpec[];
}

/** The loaded, typed config. Import this everywhere instead of re-reading JSON. */
export const config: AutomationConfig = rawConfig as AutomationConfig;

export default config;
