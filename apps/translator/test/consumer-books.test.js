import test from "node:test";
import assert from "node:assert/strict";

import { consumerBookId } from "../src/workflow/consumerBooks.js";

test("Translator uses the shared Tito consumer ID", () => {
  assert.equal(consumerBookId("titus"), "tito");
});

test("Translator leaves ordinary source IDs unchanged", () => {
  assert.equal(consumerBookId("romanos"), "romanos");
  assert.equal(consumerBookId("filemon"), "filemon");
});
