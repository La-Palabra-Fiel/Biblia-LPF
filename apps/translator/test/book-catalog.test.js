import test from "node:test";
import assert from "node:assert/strict";

import { findBook } from "../src/data/bookCatalog.js";

test("findBook accepts canonical and accented Spanish slugs", () => {
  assert.equal(findBook("philemon")?.id, "philemon");
  assert.equal(findBook("filemon")?.id, "philemon");
  assert.equal(findBook("filemón")?.id, "philemon");
});
