const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const html = fs.readFileSync(path.join(__dirname, "public/index.html"), "utf8");
const source = html.match(/^function reviewStatus\(row\)\{[\s\S]*?^\}/m)?.[0];
assert.ok(source, "Load reviewStatus from the Team Desk UI");
const ui = vm.createContext({alignmentFindingsFor: () => []});
vm.runInContext(source, ui);

function cleanRow() {
  return {
    candidate: {spanish: "Texto", uncertainties: [], addedConcepts: []},
    gate: {source: "draft-team-gpt.json", spanish: "pass", fidelity: "not-required"},
    recovered: {},
  };
}

test("an untouched prepared candidate is shown as clean", () => {
  assert.equal(ui.reviewStatus(cleanRow()), "clean");
});

test("a real recovered browser edit is not advertised as bulk-clean", () => {
  const row = cleanRow();
  row.recovered = {spanish: "Texto revisado"};
  assert.equal(ui.reviewStatus(row), "hold");
});

test("a canonical local seed is not advertised as a prepared candidate", () => {
  const row = cleanRow();
  row.gate.source = "canonical-local-seed";
  assert.equal(ui.reviewStatus(row), "missing");
});
