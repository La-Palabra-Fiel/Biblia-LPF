import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync, mkdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { execFileSync } from "node:child_process";
import { readSourcePublication } from "../src/workflow/sourcePublication.js";
import { statusRow } from "../src/workflow/bookWorkflow.js";

test("source preflight detects divergence, checks the selected book, and never changes either branch", async () => {
  const root = mkdtempSync(join(tmpdir(), "lbf-source-publication-"));
  const remote = join(root, "remote.git");
  const local = join(root, "local");
  const other = join(root, "other");
  const git = (cwd, ...args) => execFileSync("git", args, { cwd, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }).trim();
  const configure = cwd => {
    git(cwd, "config", "user.name", "Test");
    git(cwd, "config", "user.email", "test@example.com");
  };
  const draft = "| habacuc | ot | draft | none | | | | | |\n";
  const done = "| habacuc | ot | done | done | John | 2026-11-06 | John | 2026-11-06 | |\n";
  try {
    git(root, "init", "--bare", "--initial-branch=main", remote);
    git(root, "clone", remote, local);
    configure(local);
    mkdirSync(join(local, "translation/ot"), { recursive: true });
    mkdirSync(join(local, "alignment/ot/habacuc"), { recursive: true });
    writeFileSync(join(local, "translation/ot/habacuc.md"), "approved text\n");
    writeFileSync(join(local, "alignment/ot/habacuc/links.json"), "{}\n");
    writeFileSync(join(local, "STATUS.md"), draft);
    git(local, "add", ".");
    git(local, "commit", "-m", "base");
    git(local, "push", "origin", "main");
    git(root, "clone", remote, other);
    configure(other);
    writeFileSync(join(other, "unrelated.txt"), "other work\n");
    git(other, "add", ".");
    git(other, "commit", "-m", "other work");
    git(other, "push", "origin", "main");
    writeFileSync(join(local, "STATUS.md"), done);
    git(local, "add", "STATUS.md");
    git(local, "commit", "-m", "human approval");
    const headBefore = git(local, "rev-parse", "HEAD");
    const remoteBefore = git(root, "--git-dir", remote, "rev-parse", "main");
    const runGit = async args => {
      try { return { ok: true, stdout: git(local, ...args) }; }
      catch (error) { return { ok: false, code: error.status, stdout: String(error.stdout || "").trim() }; }
    };
    const options = { runGit, book: "habacuc", translation: "translation/ot/habacuc.md", alignment: "alignment/ot/habacuc", liveRow: statusRow(done, "habacuc") };
    const result = await readSourcePublication(options);
    assert.equal(result.checked, true);
    assert.equal(result.ahead, 1);
    assert.equal(result.behind, 1);
    assert.equal(result.bookOnMain, false);
    assert.match(result.message, /diverged/);
    assert.match(result.message, /approval row is not on origin\/main/);
    assert.equal(git(local, "rev-parse", "HEAD"), headBefore);
    assert.equal(git(root, "--git-dir", remote, "rev-parse", "main"), remoteBefore);
    assert.equal(git(local, "status", "--porcelain"), "");

    // Identical book state remains current despite unrelated commits in both branches.
    writeFileSync(join(other, "STATUS.md"), done);
    git(other, "add", "STATUS.md");
    git(other, "commit", "-m", "same approval delivered");
    git(other, "push", "origin", "main");
    assert.equal((await readSourcePublication(options)).bookOnMain, true);

    const offline = await readSourcePublication({ ...options, runGit: async () => ({ ok: false }) });
    assert.equal(offline.checked, false);
    assert.equal(offline.bookOnMain, false);
    assert.match(offline.message, /Could not check/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
