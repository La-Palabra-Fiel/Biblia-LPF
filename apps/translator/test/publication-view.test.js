import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";

const main = readFileSync(new URL("../public/main.js", import.meta.url), "utf8");
const render = main.slice(
  main.indexOf("function renderBookWorkflow(payload) {"),
  main.indexOf("async function loadBookWorkflow() {")
);

function renderPublication({ published, exported = false, sourcePublication }) {
  const steps = {};
  const view = {
    state: { bookId: "habacuc", workflowBusy: false, publishBusy: false, commitBusy: false },
    pendingAlignmentWork: () => [],
    document: { querySelector: () => view.sourceNotice },
    setWorkflowStep: (id, status) => { steps[id] = status; }
  };
  for (const name of [
    "workflowTranslationState", "workflowAlignmentState", "workflowCommitState",
    "workflowExportState", "workflowPublishState", "workflowPublicationState",
    "publicationHandoff", "publicationPushCommand", "publicationPrLink",
    "publicationCopyStatus", "verifyTranslationButton", "approveTranslationButton",
    "continueAlignmentButton", "verifyAlignmentButton", "approveAlignmentButton",
    "reviewCommitButton", "exportBookButton", "publishBookButton", "workflowSummary"
  ]) view[name] = { dataset: {} };
  view.sourceNotice = { dataset: {} };
  const payload = {
    row: { translation: "done", alignment: "done" },
    provenance: { committed: true, sourceCommit: "later-unrelated-commit" },
    export: {
      ready: exported,
      sourceCommit: "original-publication-commit",
      packageDir: "/tmp/lbf-export",
      problem: "The exported package does not match the current source commit. Export this book again."
    },
    publisher: { publishedToMain: published, localBranchReady: published },
    sourcePublication,
    progress: { verses: 56, alignment: { hand: 56 } },
    workflow: { nextAction: published ? "complete" : exported ? "publish" : "export" }
  };
  runInNewContext(`${render}\nrenderBookWorkflow(payload);`, { ...view, payload });
  return { view, steps };
}

test("confirmed publication stays complete after an unrelated source commit makes the local export stale", () => {
  const { view, steps } = renderPublication({ published: true });
  for (const id of ["workflow-export", "workflow-publish", "workflow-publication"]) {
    assert.equal(steps[id], "complete");
  }
  assert.equal(view.exportBookButton.disabled, true);
  assert.equal(view.exportBookButton.textContent, "Exported");
  assert.match(view.workflowExportState.textContent, /no new export needed/);
  assert.match(view.workflowSummary.textContent, /Publication is complete/);
});

test("an unpublished stale package still requires canonical export", () => {
  const { view, steps } = renderPublication({ published: false });
  assert.equal(steps["workflow-export"], "active");
  assert.equal(view.exportBookButton.disabled, false);
  assert.match(view.workflowExportState.textContent, /Export this book again/);
});

test("an unpublished current package remains ready for publisher preparation", () => {
  const { view, steps } = renderPublication({ published: false, exported: true });
  assert.equal(steps["workflow-export"], "complete");
  assert.equal(view.exportBookButton.disabled, true);
  assert.equal(view.publishBookButton.disabled, false);
  assert.match(view.workflowExportState.textContent, /Package ready/);
});

test("data publication does not hide approvals that are still local", () => {
  const { view, steps } = renderPublication({
    published: true,
    sourcePublication: { checked: true, bookOnMain: false, message: "Source branches have diverged." }
  });
  assert.equal(steps["workflow-publication"], "complete");
  assert.match(view.workflowSummary.textContent, /separate delivery/);
  assert.equal(view.sourceNotice.hidden, false);
  assert.equal(view.sourceNotice.dataset.state, "pending");
  assert.match(view.sourceNotice.textContent, /diverged/);
});
