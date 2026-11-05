const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const html = fs.readFileSync(path.join(__dirname, "public/index.html"), "utf8");
const functions = [
  html.match(/^function reviewStatus\(row\)\{[\s\S]*?^\}/m)?.[0],
  html.match(/^function alignmentFindingsFor\(row\).*$/m)?.[0],
  html.match(/^function decorateAlignmentCard\(card,row\)\{[\s\S]*?^\}/m)?.[0],
];
assert.ok(functions.every(Boolean), "Load the actual review-queue functions");
let refreshes = 0;
const ui = vm.createContext({
  refreshTokenSpanish: () => { refreshes++; },
  document: { createElement: () => { throw Error("Unexpected stale diagnostic panel"); } },
});
vm.runInContext(functions.join("\n"), ui);

function rowWithHistoricalFinding() {
  return {
    candidate: {
      spanish: "de Betel",
      alignmentPrecisionFindings: [{
        severity: "fail", spanishSpan: "de Betel",
        issue: "The alignment unit combines independently alignable proper names",
        sourceTokenIds: ["h01012008005", "h01012008006"],
      }],
    },
    gate: { source: "draft.json", alignmentFindings: [], spanish: "pass", fidelity: "not-required" },
  };
}

test("resolved Betel finding does not appear in the queue or diagnostic panel", () => {
  const row = rowWithHistoricalFinding();
  assert.equal(ui.alignmentFindingsFor(row).length, 0);
  assert.equal(ui.reviewStatus(row), "clean");
  const card = {};
  const before = refreshes;
  ui.decorateAlignmentCard(card, row);
  assert.equal(card._alignmentFindings.length, 0);
  assert.equal(refreshes, before + 1);
  assert.equal(row.candidate.alignmentPrecisionFindings.length, 1);
});

test("current findings still populate the alignment queue and are deduplicated", () => {
  const row = rowWithHistoricalFinding();
  const current = { severity: "fail", issue: "Independent names", spanishSpan: "Betel y Hai", sourceTokenIds: ["h1", "h2", "h3"] };
  row.gate.alignmentFindings = [current, { ...current }];
  assert.equal(ui.alignmentFindingsFor(row).length, 1);
  assert.equal(ui.reviewStatus(row), "alignment");
});

test("clearing historical precision warnings does not clear fidelity or uncertainty holds", () => {
  const row = rowWithHistoricalFinding();
  row.candidate.uncertainties = [{ issue: "Unresolved meaning" }];
  assert.equal(ui.reviewStatus(row), "hold");
  row.candidate.uncertainties = [];
  row.gate.fidelity = "fail";
  assert.equal(ui.reviewStatus(row), "hold");
});
