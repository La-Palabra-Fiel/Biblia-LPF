#!/usr/bin/env node
/** Offline comparison and dry-run preparation; it never calls a provider. */
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import { buildContextWindowRequest } from "./src/candidate-scan.js";
import { compactScanPayload, compactSizeComparison, validateCompactScanPayload } from "./src/candidate-scan-compact.js";

const appRoot = fileURLToPath(new URL(".", import.meta.url));
const repoRoot = fileURLToPath(new URL("../..", import.meta.url));
const trancheDirectory = join(appRoot, "var", "openrouter-jev-ot-discovery-tranche-v0.1.0");
const outputDirectory = join(appRoot, "var", "compact-ot-scan-v0.2.0");
const ledger = JSON.parse(await readFile(join(appRoot, "var", "candidate-scan-v0.1.0", "ledger.json"), "utf8"));
const index = JSON.parse(await readFile(join(trancheDirectory, "index.json"), "utf8"));
await mkdir(outputDirectory, { recursive: true });
const compactFileName = windowId => `${String(windowId).replaceAll(":", ".")}.compact-dry-run.json`;
const comparison = [];
for (const attempt of index.attempts.filter(item => item.status === "succeeded")) {
  const record = JSON.parse(await readFile(join(trancheDirectory, attempt.file), "utf8"));
  const compacted = compactScanPayload(record.exact_api_request), validation = validateCompactScanPayload(compacted, record.exact_api_request), sizes = compactSizeComparison(record.exact_api_request, compacted);
  if (!validation.ok) throw new Error(`Compact comparison failed for ${attempt.window_id}: ${validation.errors.join(", ")}`);
  const file = compactFileName(attempt.window_id);
  await writeFile(join(outputDirectory, file), `${JSON.stringify({ source_attempt: { file: attempt.file, request_fingerprint: attempt.request_fingerprint }, compact_payload: compacted.payload, local_record: compacted.local_record, validation, sizes }, null, 2)}\n`);
  comparison.push({ window_id: attempt.window_id, source_attempt_file: attempt.file, compact_file: file, ...sizes, validation });
}
const genesis = [];
for (const window of ledger.sequential_roster_cursor?.proposed_next_tranche || []) {
  const full = await buildContextWindowRequest(repoRoot, { book: window.book, chapter: window.chapter, firstVerse: window.first_verse, lastVerse: window.last_verse });
  const compacted = compactScanPayload(full), validation = validateCompactScanPayload(compacted, full), sizes = compactSizeComparison(full, compacted);
  if (!validation.ok) throw new Error(`Genesis compact preparation failed for ${window.window_id}: ${validation.errors.join(", ")}`);
  const file = compactFileName(window.window_id);
  await writeFile(join(outputDirectory, file), `${JSON.stringify({ planned_window: window, compact_payload: compacted.payload, local_record: compacted.local_record, validation, sizes }, null, 2)}\n`);
  genesis.push({ window_id: window.window_id, compact_file: file, ...sizes, validation });
}
const sum = (items, key) => items.reduce((total, item) => total + item[key], 0);
const report = {
  schema_version: "0.1.0", mode: "dry_run_only", frozen_prompt_version: ledger.frozen_prompt_version,
  api_repetition_observations: {
    established_from_saved_successful_requests: "Questions used type: choice and an individual criteria object. The response validator derives allowed answer keys from that per-question object.",
    retained: "type and criteria option keys are retained per question. Criteria prose is replaced by references to one shared definition map.",
    not_established_without_a_paid_call: "The endpoint has not been tested with criteria omitted entirely, so the compact serializer does not assume that omission is accepted."
  },
  saved_tranche_comparison: { windows: comparison, totals: { full_bytes: sum(comparison, "full_bytes"), compact_bytes: sum(comparison, "compact_bytes"), saved_bytes: sum(comparison, "saved_bytes"), reduction_percent: Number(((sum(comparison, "saved_bytes") / sum(comparison, "full_bytes")) * 100).toFixed(2)), rough_full_input_tokens: sum(comparison, "rough_full_input_tokens"), rough_compact_input_tokens: sum(comparison, "rough_compact_input_tokens") } },
  prepared_sequential_genesis_tranche: { windows: genesis, totals: { full_bytes: sum(genesis, "full_bytes"), compact_bytes: sum(genesis, "compact_bytes"), saved_bytes: sum(genesis, "saved_bytes"), reduction_percent: Number(((sum(genesis, "saved_bytes") / sum(genesis, "full_bytes")) * 100).toFixed(2)), rough_full_input_tokens: sum(genesis, "rough_full_input_tokens"), rough_compact_input_tokens: sum(genesis, "rough_compact_input_tokens") } }
};
await writeFile(join(outputDirectory, "comparison.json"), `${JSON.stringify(report, null, 2)}\n`);
console.log(JSON.stringify(report));
