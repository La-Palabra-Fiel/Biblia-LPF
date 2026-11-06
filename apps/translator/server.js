import { createServer } from "node:http";
import { execFile } from "node:child_process";
import { existsSync, readdirSync } from "node:fs";
import { appendFile, mkdir, mkdtemp, readFile, readdir, rm, stat, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { basename, dirname, extname, join, normalize, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import { getCgvDataPath, getGreekConstructionEvidence, getGreekOccurrencesByStrongs, getHebrewOccurrencesByStrongs } from "./src/data/cgvData.js";
import { loadTranslationIndexes, resolveAlignedSpan, lookupRv1909AquiferVerse } from "./src/data/translationIndexes.js";
import { describeAiAvailability, loadTranslatorEnv } from "./src/ai/suggestPhrase.js";
import { analyzePhraseGates } from "./src/pipeline/analyzeGates.js";
import { assistPhraseGates } from "./src/pipeline/assistGates.js";
import { createInvestigationFromLemma, languageFromStrongs } from "./src/investigations/createInvestigation.js";
import { findBook, allTranslatorBooks, lbfHome } from "./src/data/bookCatalog.js";
import { loadNtBookUnits } from "./src/data/morphLoader.js";
import { parseTranslationBook, replaceTranslationVerse } from "./src/reader/translationReader.js";
import {
  approveStage,
  formatStatusRow,
  invalidateAfterEdit,
  replaceStatusRow,
  statusRow,
  workflowForRow
} from "./src/workflow/bookWorkflow.js";
import { readSourcePublication } from "./src/workflow/sourcePublication.js";

const rootDir = fileURLToPath(new URL(".", import.meta.url));
await loadTranslatorEnv(rootDir);
const publicDir = join(rootDir, "public");
const investigationsDir = join(rootDir, "investigations");
const repoRoot = join(rootDir, "..", "..");
const statusFile = join(repoRoot, "STATUS.md");
const exportPackageDir = "/tmp/lbf-export";
const defaultDataRepo = resolve(repoRoot, "..", "cgv-data");
const port = Number(process.env.PORT || 1424);
const execFileAsync = promisify(execFile);

function resolveBook(bookId) {
  const book = findBook(bookId);
  if (!book) {
    throw new Error(`Unknown Translator book: ${bookId}`);
  }
  return book;
}

function bookIdFromRequest(url, body = null) {
  return resolveBook(
    url.searchParams.get("book")
    || body?.book
    || process.env.CGV_TRANSLATOR_BOOK
    || "titus"
  ).id;
}

function translationPathsForBook(bookId) {
  const book = resolveBook(bookId);
  const { slug, testament } = lbfHome(book);
  const alignDir = join(repoRoot, "alignment", testament, slug);
  const documentFile = join(repoRoot, "translation", testament, `${slug}.md`);
  if (book.spine === "oshb") {
    const phraseFile = join(alignDir, `${slug}-phrases.json`);
    return {
      book,
      phraseFile,
      defaultPhraseFile: phraseFile,
      documentFile,
      reverseLinksFile: join(alignDir, `${slug}-reverse-links.json`),
      spineKind: "oshb"
    };
  }
  const phraseFile = join(alignDir, `${slug}-phrases-tr.json`);
  return {
    book,
    phraseFile,
    defaultPhraseFile: phraseFile,
    documentFile,
    reverseLinksFile: join(alignDir, `${slug}-reverse-links.json`),
    spineKind: "tr"
  };
}

async function resolvePhraseFile(bookId) {
  const paths = translationPathsForBook(bookId);
  const { book, phraseFile, defaultPhraseFile, documentFile, spineKind } = paths;
  if (spineKind === "oshb") {
    try {
      await stat(phraseFile);
      return { book, phraseFile, documentFile, textualBasis: "OSHB/WLC", spineKind };
    } catch {
      return { book, phraseFile: defaultPhraseFile, documentFile, textualBasis: "OSHB/WLC", spineKind };
    }
  }
  try {
    await stat(phraseFile);
    return { book, phraseFile, documentFile, textualBasis: "Scrivener 1894 TR", spineKind: "tr" };
  } catch {
    return { book, phraseFile: defaultPhraseFile, documentFile, textualBasis: "MorphGNT/SBLGNT (fallback)", spineKind: "morph" };
  }
}
const bibliaBleOutputDir = join(rootDir, "..", "Biblia-BLE", "output");
const mnaMorphgntDir = join(rootDir, "..", "MNA", "SOURCES", "MorphGNT");
const mnaInterlinearDir = join(rootDir, "..", "MNA", "datasets", "interlinear", "NT");
const bleGlossBulletMarks = new Set(["de", "a", "en", "por", "para", "con", "sin", "que", "medio", "causa"]);
const bleGlossSplits = { del: ["de"], al: ["a", "el"] };
let bleTokenGlossIndexPromise = null;

async function readFirstExistingFile(candidates) {
  for (const candidate of candidates) {
    try {
      return await readFile(candidate, "utf8");
    } catch {
      // Try the next candidate path.
    }
  }
  return "";
}

const tabs = [
  { id: "README", file: "README.md" },
  { id: "Observations", file: "observations.md" },
  { id: "Decision", file: "decision.md" },
  { id: "Questions", file: "questions.md" },
  { id: "Evidence", file: "evidence.md" },
  { id: "Research", file: "research.md" },
  { id: "Policy", file: "policy.md" },
  { id: "History", file: "history.md" }
];

const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml"
};

function send(response, status, body, contentType = "text/plain; charset=utf-8") {
  response.writeHead(status, {
    "Content-Type": contentType,
    "Cache-Control": "no-store"
  });
  response.end(body);
}

function sendJson(response, status, body) {
  send(response, status, JSON.stringify(body), "application/json; charset=utf-8");
}

function normalizeTokenRow(row = {}) {
  const surface = typeof row.surface === "string" ? row.surface : "";
  const greek = typeof row.greek === "string" && row.greek.trim()
    ? row.greek
    : surface;
  const ble = typeof row.ble === "string" && row.ble.trim()
    ? row.ble
    : (typeof row.es === "string" ? row.es : "");
  return {
    ...row,
    sourceTokenId: row.sourceTokenId != null ? String(row.sourceTokenId) : "",
    greek,
    surface: surface || greek,
    lemma: typeof row.lemma === "string" ? row.lemma : "",
    strongs: typeof row.strongs === "string" ? row.strongs : "",
    rmac: typeof row.rmac === "string" ? row.rmac : (typeof row.morph === "string" ? row.morph : ""),
    morphology: typeof row.morphology === "string" ? row.morphology : "",
    ble,
    rv1909: typeof row.rv1909 === "string" ? row.rv1909 : ""
  };
}

function extractPhraseArray(value) {
  if (Array.isArray(value)) return value;
  if (value && typeof value === "object" && Array.isArray(value.phrases)) return value.phrases;
  return [];
}

function normalizeTranslationPhrases(value) {
  return extractPhraseArray(value)
    .map((item, index) => {
      const tokenRows = Array.isArray(item.tokenRows)
        ? item.tokenRows.map(normalizeTokenRow)
        : [];
      const sourceTokenIds = Array.isArray(item.sourceTokenIds) && item.sourceTokenIds.length
        ? item.sourceTokenIds.map(String)
        : tokenRows.map(row => row.sourceTokenId).filter(Boolean);
      const greekFromTokens = tokenRows.map(row => row.greek).filter(Boolean).join(" ");
      const hebrew = typeof item.hebrew === "string" ? item.hebrew : "";
      const greek = typeof item.greek === "string" && item.greek.trim()
        ? item.greek
        : (hebrew || greekFromTokens);
      return {
        reference: typeof item.reference === "string" && item.reference.trim()
          ? item.reference.trim()
          : "Titus 1:1",
        phraseIndex: Number.isInteger(Number(item.phraseIndex)) ? Number(item.phraseIndex) : index,
        hebrew,
        greek,
        spanish: typeof item.spanish === "string" ? item.spanish : "",
        sourceTokenIds,
        tokenRows,
        rv1909Text: typeof item.rv1909Text === "string" ? item.rv1909Text : "",
        bleText: typeof item.bleText === "string" ? item.bleText : "",
        suggestionSource: typeof item.suggestionSource === "string" ? item.suggestionSource : "",
        approval: item && typeof item.approval === "object" && item.approval ? item.approval : undefined,
        chapter: item.chapter,
        verse: item.verse,
        mtChapter: item.mtChapter,
        mtVerse: item.mtVerse
      };
    })
    .filter(item => item.phraseIndex >= 0)
    .sort((a, b) => a.phraseIndex - b.phraseIndex);
}

function phraseIndexKey(phrase) {
  return Number(phrase.phraseIndex);
}

async function readExistingTranslationPhrases(phraseFile) {
  const phraseContent = await readFile(phraseFile, "utf8").catch(() => "");
  if (!phraseContent) return [];
  try {
    return normalizeTranslationPhrases(JSON.parse(phraseContent));
  } catch {
    return [];
  }
}

function toOshbPhraseRecord(phrase) {
  const tokenRows = Array.isArray(phrase.tokenRows)
    ? phrase.tokenRows.map(row => ({
      sourceTokenId: row.sourceTokenId || "",
      surface: row.surface || row.greek || "",
      lemma: row.lemma || "",
      morph: row.morph || row.rmac || "",
      ...(row.lang ? { lang: row.lang } : {}),
      ...(row.oshbId ? { oshbId: row.oshbId } : {})
    }))
    : [];
  return {
    phraseIndex: phrase.phraseIndex,
    reference: phrase.reference,
    chapter: phrase.chapter,
    verse: phrase.verse,
    spanish: phrase.spanish || "",
    hebrew: phrase.hebrew || phrase.greek || "",
    sourceTokenIds: Array.isArray(phrase.sourceTokenIds) ? phrase.sourceTokenIds : [],
    tokenRows
  };
}

async function writeTranslationPhrases(phraseFile, phrases, book, textualBasis) {
  await mkdir(dirname(phraseFile), { recursive: true });
  if (book?.spine === "oshb") {
    let existing = null;
    try {
      existing = JSON.parse(await readFile(phraseFile, "utf8"));
    } catch {
      existing = null;
    }
    if (Array.isArray(existing) || existing == null) {
      await writeFile(
        phraseFile,
        `${JSON.stringify(phrases.map(toOshbPhraseRecord), null, 2)}\n`,
        "utf8"
      );
      return;
    }
    const doc = {
      ...existing,
      bookId: book.id,
      textualBasis: existing.textualBasis || textualBasis || "OSHB/WLC",
      schemaVersion: existing.schemaVersion || 1,
      phrases
    };
    await writeFile(phraseFile, `${JSON.stringify(doc, null, 2)}\n`, "utf8");
    return;
  }
  await writeFile(phraseFile, `${JSON.stringify(phrases, null, 2)}\n`, "utf8");
}

/**
 * Merge client saves into disk so a stale browser tab cannot:
 * - shrink the phrase list
 * - wipe non-empty preliminary Spanish with blanks
 *
 * Phrase identity is phraseIndex (book-wide), not reference alone.
 */
function mergeTranslationPhraseSaves(incoming, existing) {
  const existingByIndex = new Map(existing.map(item => [phraseIndexKey(item), item]));
  const seen = new Set();
  const merged = [];

  for (const item of incoming) {
    const key = phraseIndexKey(item);
    if (!Number.isInteger(key) || key < 0 || seen.has(key)) continue;
    seen.add(key);
    const prev = existingByIndex.get(key);
    if (!prev) {
      // Do not let a stale tab invent sparse blank rows beyond the seed.
      if (!String(item.spanish || "").trim() && existing.length) continue;
      merged.push(item);
      continue;
    }

    const incomingSpanish = String(item.spanish || "").trim();
    const previousSpanish = String(prev.spanish || "").trim();
    const spanish = incomingSpanish || previousSpanish;
    const suggestionSource = incomingSpanish
      ? (item.suggestionSource || prev.suggestionSource || "")
      : (prev.suggestionSource || item.suggestionSource || "");

    merged.push({
      ...prev,
      phraseIndex: key,
      // Keep seed identity stable; client may only revise Spanish (+ source label).
      reference: prev.reference,
      hebrew: prev.hebrew || item.hebrew || "",
      greek: prev.greek || item.greek || prev.hebrew || item.hebrew || "",
      sourceTokenIds: prev.sourceTokenIds?.length ? prev.sourceTokenIds : item.sourceTokenIds,
      rv1909Text: item.rv1909Text || prev.rv1909Text || "",
      bleText: item.bleText || prev.bleText || "",
      spanish,
      suggestionSource,
      approval: item.approval || prev.approval
    });
  }

  for (const prev of existing) {
    const key = phraseIndexKey(prev);
    if (!seen.has(key)) merged.push(prev);
  }

  return merged.sort((a, b) => a.phraseIndex - b.phraseIndex);
}

function investigationBookFromId(id) {
  const match = String(id || "").match(/^INV-(\d{2})-(\d{4})$/);
  if (!match) {
    throw new Error("Invalid investigation ID");
  }
  const bookNumber = Number(match[1]);
  const book = allTranslatorBooks().find(item => Number(item.number) === bookNumber);
  if (!book) {
    throw new Error(`Unknown investigation book number: ${match[1]}`);
  }
  return book;
}

function safeInvestigationPath(id) {
  const book = investigationBookFromId(id);
  const candidate = join(investigationsDir, book.id, id);
  if (existsSync(candidate)) return candidate;
  throw new Error(`Investigation not found: ${id}`);
}

function safeTabFile(file) {
  const tab = tabs.find(item => item.file === file);
  if (!tab) {
    throw new Error("Invalid investigation file");
  }
  return tab;
}

function safeEvidenceFile(file) {
  if (!/^[a-z0-9-]+\.(?:md|json)$/.test(file)) {
    throw new Error("Invalid evidence file");
  }
  return file;
}

function todayIsoDate() {
  return new Date().toLocaleDateString("en-CA", { timeZone: "America/La_Paz" });
}

function shellSingleQuote(value) {
  return `'${String(value).replaceAll("'", `'"'"'`)}'`;
}

async function runCanonicalTool(script, bookSlug) {
  try {
    const result = await execFileAsync("python3", [join(repoRoot, "tools", script), bookSlug], {
      cwd: repoRoot,
      encoding: "utf8",
      maxBuffer: 8 * 1024 * 1024
    });
    return { ok: true, output: `${result.stdout || ""}${result.stderr || ""}`.trim() };
  } catch (error) {
    return {
      ok: false,
      code: Number(error?.code) || 1,
      output: `${error?.stdout || ""}${error?.stderr || ""}`.trim() || error.message
    };
  }
}

async function runCanonicalPublisher(bookSlug, dataRepo) {
  try {
    const result = await execFileAsync("python3", [
      join(repoRoot, "tools", "publish.py"),
      bookSlug,
      "--data-repo",
      dataRepo
    ], {
      cwd: repoRoot,
      encoding: "utf8",
      maxBuffer: 8 * 1024 * 1024
    });
    return { ok: true, output: `${result.stdout || ""}${result.stderr || ""}`.trim() };
  } catch (error) {
    return {
      ok: false,
      code: Number(error?.code) || 1,
      output: `${error?.stdout || ""}${error?.stderr || ""}`.trim() || error.message
    };
  }
}

async function runGit(args, { allowFailure = false, timeoutMs } = {}) {
  try {
    const result = await execFileAsync("git", args, {
      cwd: repoRoot,
      encoding: "utf8",
      timeout: timeoutMs,
      maxBuffer: 8 * 1024 * 1024
    });
    return { ok: true, stdout: String(result.stdout || "").trim(), stderr: String(result.stderr || "").trim() };
  } catch (error) {
    const result = {
      ok: false,
      code: Number(error?.code) || 1,
      stdout: String(error?.stdout || "").trim(),
      stderr: String(error?.stderr || "").trim()
    };
    if (allowFailure) return result;
    throw new Error(result.stderr || result.stdout || error.message);
  }
}

function gitPathsForBook(bookId) {
  const book = resolveBook(bookId);
  const { slug, testament } = lbfHome(book);
  return {
    book,
    slug,
    testament,
    translation: `translation/${testament}/${slug}.md`,
    alignment: `alignment/${testament}/${slug}`
  };
}

function porcelainPath(line = "") {
  const path = String(line).slice(3).trim();
  return path.includes(" -> ") ? path.split(" -> ").at(-1) : path;
}

async function readBookProvenance(bookId) {
  const paths = gitPathsForBook(bookId);
  const [workingStatus, headStatusResult, changesResult, stagedResult, headResult] = await Promise.all([
    readFile(statusFile, "utf8"),
    runGit(["show", "HEAD:STATUS.md"], { allowFailure: true }),
    runGit(["status", "--porcelain=v1", "--untracked-files=all", "--", paths.translation, paths.alignment]),
    runGit(["diff", "--cached", "--name-only"]),
    runGit(["rev-parse", "--short", "HEAD"])
  ]);
  const liveRow = statusRow(workingStatus, paths.slug);
  const headRow = headStatusResult.ok ? statusRow(headStatusResult.stdout, paths.slug) : null;
  const statusCommitted = Boolean(liveRow && headRow && formatStatusRow(liveRow) === formatStatusRow(headRow));
  const changes = changesResult.stdout
    ? changesResult.stdout.split("\n").filter(Boolean).map(line => ({ status: line.slice(0, 2), path: porcelainPath(line) }))
    : [];
  if (!statusCommitted) changes.push({ status: " M", path: "STATUS.md (selected book row)" });
  const stagedChanges = stagedResult.stdout ? stagedResult.stdout.split("\n").filter(Boolean) : [];
  return {
    committed: changes.length === 0,
    sourceCommit: headResult.stdout,
    changes,
    stagedChanges,
    commitBlocked: stagedChanges.length > 0,
    defaultMessage: `Finish ${paths.slug} translation and alignment`
  };
}

async function readExportState(bookId) {
  const { slug } = gitPathsForBook(bookId);
  const textFile = join(exportPackageDir, `${slug}.lbf.md`);
  const alignmentFile = join(exportPackageDir, `${slug}.alignment.json`);
  try {
    const [text, alignmentRaw, head] = await Promise.all([
      readFile(textFile, "utf8"),
      readFile(alignmentFile, "utf8"),
      runGit(["rev-parse", "HEAD"])
    ]);
    const alignment = JSON.parse(alignmentRaw);
    const textCommit = text.match(/^\s*sourceCommit:\s*([0-9a-f]{40})\s*$/mu)?.[1] || "";
    const alignmentCommit = String(alignment.sourceCommit || "");
    const ready = Boolean(textCommit && textCommit === alignmentCommit && textCommit === head.stdout);
    return {
      ready,
      sourceCommit: alignmentCommit,
      publishedAt: String(alignment.publishedAt || ""),
      packageDir: exportPackageDir,
      problem: ready ? "" : "The exported package does not match the current source commit. Export this book again."
    };
  } catch {
    return {
      ready: false,
      sourceCommit: "",
      publishedAt: "",
      packageDir: exportPackageDir,
      problem: "No current exported package was found for this book."
    };
  }
}

async function runDataGit(args, { allowFailure = false } = {}) {
  try {
    const result = await execFileAsync("git", args, {
      cwd: defaultDataRepo,
      encoding: "utf8",
      maxBuffer: 8 * 1024 * 1024
    });
    return { ok: true, stdout: String(result.stdout || "").trim(), stderr: String(result.stderr || "").trim() };
  } catch (error) {
    const result = {
      ok: false,
      stdout: String(error?.stdout || "").trim(),
      stderr: String(error?.stderr || "").trim()
    };
    if (allowFailure) return result;
    throw new Error(result.stderr || result.stdout || error.message);
  }
}

async function readPublishedBookFromRef(bookSlug, ref) {
  try {
    const [textResult, alignmentResult] = await Promise.all([
      execFileAsync("git", [
        "-C",
        defaultDataRepo,
        "show",
        `${ref}:bibles/LBF/${bookSlug}.lbf.md`
      ], { encoding: "utf8", maxBuffer: 8 * 1024 * 1024 }),
      execFileAsync("git", [
        "-C",
        defaultDataRepo,
        "show",
        `${ref}:bibles/LBF/alignments/${bookSlug}.alignment.json`
      ], { encoding: "utf8", maxBuffer: 8 * 1024 * 1024 })
    ]);
    const textCommit = String(textResult.stdout || "").match(/^\s*sourceCommit:\s*([0-9a-f]{40})\s*$/mu)?.[1] || "";
    const alignment = JSON.parse(String(alignmentResult.stdout || "{}"));
    const alignmentCommit = String(alignment.sourceCommit || "");
    if (!textCommit || textCommit !== alignmentCommit) return null;
    return {
      sourceCommit: textCommit,
      publishedAt: String(alignment.publishedAt || "")
    };
  } catch {
    return null;
  }
}

async function bookContentUnchangedSince(bookSlug, sourceCommit) {
  if (!sourceCommit) return false;
  const paths = gitPathsForBook(bookSlug);
  const result = await runGit([
    "diff",
    "--quiet",
    sourceCommit,
    "HEAD",
    "--",
    paths.translation,
    paths.alignment
  ], { allowFailure: true });
  // exit 0 = unchanged, exit 1 = changed, other = missing commit / error
  return result.ok;
}

async function readLocalPublicationState(bookSlug, exported) {
  const available = existsSync(join(defaultDataRepo, ".git"));
  const stamp = String(exported.publishedAt || "").match(/^(\d{4})-(\d{2})-(\d{2})T/u);
  let branch = stamp ? `lbf-${bookSlug}-${stamp.slice(1).join("")}` : "";
  const pullRequestUrlFor = name => (name
    ? `https://github.com/Cultivados-en-Gracia-y-Verdad/cgv-data/compare/main...${name}?expand=1`
    : "");
  const pushCommandFor = name => (name
    ? `git -C ${shellSingleQuote(defaultDataRepo)} push -u origin ${name}`
    : "");
  const empty = {
    defaultDataRepo,
    destinationAvailable: available,
    localBranchReady: false,
    publishedToMain: false,
    branch,
    pushCommand: pushCommandFor(branch),
    pullRequestUrl: pullRequestUrlFor(branch)
  };
  if (!available) return empty;

  // Refresh remote tip so a merged PR is visible without a manual fetch.
  await runDataGit(["fetch", "--quiet", "origin", "main"], { allowFailure: true });

  const onMain = await readPublishedBookFromRef(bookSlug, "origin/main");
  const publishedToMain = Boolean(
    onMain
    && (
      (exported.ready && onMain.sourceCommit === exported.sourceCommit)
      || await bookContentUnchangedSince(bookSlug, onMain.sourceCommit)
    )
  );

  if (!branch && onMain?.publishedAt) {
    const mainStamp = String(onMain.publishedAt).match(/^(\d{4})-(\d{2})-(\d{2})T/u);
    if (mainStamp) branch = `lbf-${bookSlug}-${mainStamp.slice(1).join("")}`;
  }

  const branchExists = branch
    ? (await runDataGit(["rev-parse", "--verify", branch], { allowFailure: true })).ok
      || (await runDataGit(["rev-parse", "--verify", `origin/${branch}`], { allowFailure: true })).ok
    : false;
  const onBranch = branch ? await readPublishedBookFromRef(bookSlug, branch) : null;
  const localBranchReady = publishedToMain
    || branchExists
    || Boolean(onBranch && exported.ready && onBranch.sourceCommit === exported.sourceCommit);

  return {
    ...empty,
    branch,
    pushCommand: pushCommandFor(branch),
    pullRequestUrl: pullRequestUrlFor(branch),
    localBranchReady,
    publishedToMain,
    publishedSourceCommit: onMain?.sourceCommit || ""
  };
}

async function stageSelectedStatusRow(bookSlug, liveRow) {
  const headStatus = await runGit(["show", "HEAD:STATUS.md"]);
  const replaced = replaceStatusRow(headStatus.stdout, bookSlug, () => ({ ...liveRow })).text;
  const candidate = replaced.endsWith("\n") ? replaced : `${replaced}\n`;
  const tempDir = await mkdtemp(join(tmpdir(), "lbf-status-"));
  const tempFile = join(tempDir, "STATUS.md");
  try {
    await writeFile(tempFile, candidate, "utf8");
    const blob = await runGit(["hash-object", "-w", tempFile]);
    await runGit(["update-index", "--add", "--cacheinfo", "100644", blob.stdout, "STATUS.md"]);
  } finally {
    await rm(tempDir, { recursive: true, force: true });
  }
}

async function commitFinishedBook(bookId, { message, humanConfirmation }) {
  if (humanConfirmation !== true) throw new Error("Explicit human confirmation is required before committing.");
  const commitMessage = String(message || "").trim();
  if (!commitMessage || commitMessage.length > 200 || /[\r\n]/u.test(commitMessage)) {
    throw new Error("Enter a one-line commit message between 1 and 200 characters.");
  }
  const current = await readBookWorkflow(bookId);
  if (current.row.translation !== "done" || current.row.alignment !== "done") {
    throw new Error("Translation and alignment must both be human-approved before committing.");
  }
  const validation = await runCanonicalTool("status.py", current.slug);
  if (!validation.ok) {
    const error = new Error("Canonical validation failed. Fix the selected book before committing it.");
    error.output = validation.output;
    throw error;
  }
  const before = await readBookProvenance(bookId);
  if (before.committed) return { committed: true, output: `Already committed at ${before.sourceCommit}.`, provenance: before };
  if (before.stagedChanges.length) {
    throw new Error(`Commit blocked: the Git index already contains staged work: ${before.stagedChanges.join(", ")}`);
  }

  const paths = gitPathsForBook(bookId);
  let created = false;
  try {
    await runGit(["add", "--", paths.translation, paths.alignment]);
    await stageSelectedStatusRow(paths.slug, current.row);
    const staged = await runGit(["diff", "--cached", "--name-only"]);
    const stagedPaths = staged.stdout ? staged.stdout.split("\n").filter(Boolean) : [];
    const unexpected = stagedPaths.filter(path =>
      path !== "STATUS.md"
      && path !== paths.translation
      && !path.startsWith(`${paths.alignment}/`)
    );
    if (unexpected.length) {
      throw new Error(`Refusing to commit unrelated staged files: ${unexpected.join(", ")}`);
    }
    if (!stagedPaths.length) throw new Error("No selected-book changes were staged.");
    const result = await runGit(["commit", "-m", commitMessage]);
    created = true;
    const provenance = await readBookProvenance(bookId);
    if (!provenance.committed) {
      throw new Error("The commit was created, but selected-book changes still remain uncommitted.");
    }
    return { committed: true, output: result.stdout || result.stderr, provenance };
  } finally {
    if (!created) {
      await runGit(["restore", "--staged", "--", "STATUS.md", paths.translation, paths.alignment], { allowFailure: true });
    }
  }
}

function tokenVerseIndexFromSpine(spine) {
  const tokenVerse = new Map();
  for (const [cv, verse] of Object.entries(spine?.verses || {})) {
    for (const token of verse?.tokens || []) {
      if (token?.sourceTokenId) tokenVerse.set(String(token.sourceTokenId), cv);
    }
  }
  return tokenVerse;
}

function tokenVerseIndexFromPhrases(phrases) {
  const tokenVerse = new Map();
  for (const phrase of phrases || []) {
    const cv = Number.isInteger(Number(phrase.chapter)) && Number.isInteger(Number(phrase.verse))
      ? `${Number(phrase.chapter)}:${Number(phrase.verse)}`
      : String(phrase.reference || "").match(/(\d+:\d+)\s*$/u)?.[1] || "";
    for (const row of phrase.tokenRows || []) {
      if (row?.sourceTokenId) tokenVerse.set(String(row.sourceTokenId), cv);
    }
  }
  return tokenVerse;
}

async function loadSourceTokenVerseIndex(paths) {
  const { slug } = lbfHome(paths.book);
  const alignDir = dirname(paths.reverseLinksFile);
  const spineCandidates = [
    join(alignDir, `${slug}-oshb-spine.json`),
    join(alignDir, `${slug}-tr-spine.json`)
  ];
  for (const candidate of spineCandidates) {
    try {
      const index = tokenVerseIndexFromSpine(JSON.parse(await readFile(candidate, "utf8")));
      if (index.size) return index;
    } catch {
      // Try the other canonical spine, then the phrase file.
    }
  }
  try {
    const phrases = extractPhraseArray(JSON.parse(await readFile(paths.phraseFile, "utf8")));
    const index = tokenVerseIndexFromPhrases(phrases);
    if (index.size) return index;
  } catch {
    // No phrase-token index either.
  }
  return null;
}

function alignmentMethodCounts(doc = {}) {
  const counts = { phrases: 0, hand: 0, auto: 0, gloss: 0, unwalked: 0, unconfirmed: 0, other: 0 };
  for (const link of doc.links || []) {
    counts.phrases += 1;
    const units = Array.isArray(link.units) ? link.units : [];
    const methods = units.map(unit => String(unit.method || ""));
    if (!units.length || link.status === "unwalked") counts.unwalked += 1;
    else if (methods.some(method => ["auto", "auto-zip"].includes(method))) counts.auto += 1;
    else if (methods.some(method => ["gloss", "gloss-match", "gloss-seed", "verse-span-resynchronization"].includes(method))) counts.gloss += 1;
    else if (!["hand", "manual", "manual-realign"].includes(String(link.status || ""))) counts.unconfirmed += 1;
    else if (methods.every(method => ["hand", "manual", "manual-realign"].includes(method))) counts.hand += 1;
    else counts.other += 1;
  }
  return counts;
}

async function readBookWorkflow(bookId) {
  const paths = translationPathsForBook(bookId);
  const { slug } = lbfHome(paths.book);
  const ledger = await readFile(statusFile, "utf8");
  const row = statusRow(ledger, slug);
  if (!row) throw new Error(`${slug} is not in STATUS.md`);
  const translation = await readFile(paths.documentFile, "utf8").catch(() => "");
  const alignment = await readFile(paths.reverseLinksFile, "utf8")
    .then(raw => JSON.parse(raw))
    .catch(() => ({}));
  const [provenance, exported] = await Promise.all([
    readBookProvenance(bookId),
    readExportState(bookId)
  ]);
  const sourcePaths = gitPathsForBook(bookId);
  const sourcePublication = await readSourcePublication({
    runGit, book: slug, translation: sourcePaths.translation,
    alignment: sourcePaths.alignment, liveRow: row
  });
  const workflow = workflowForRow(row);
  const alignmentProgress = alignmentMethodCounts(alignment);
  const alignmentRemaining = alignmentProgress.auto
    + alignmentProgress.gloss
    + alignmentProgress.unwalked
    + alignmentProgress.unconfirmed
    + alignmentProgress.other;
  if (row.translation === "done" && alignmentRemaining > 0) {
    workflow.finished = false;
    workflow.nextAction = "align";
  }
  if (row.translation === "done" && row.alignment === "done" && alignmentRemaining === 0) {
    workflow.nextAction = provenance.committed ? (exported.ready ? "publish" : "export") : "commit";
  }
  const publisher = await readLocalPublicationState(slug, exported);
  if (publisher.localBranchReady) workflow.nextAction = "publish-pr";
  if (publisher.publishedToMain) workflow.nextAction = "complete";
  return {
    book: paths.book.id,
    slug,
    label: paths.book.label,
    row,
    workflow,
    provenance,
    sourcePublication,
    export: exported,
    publisher,
    progress: {
      verses: (translation.match(/^###\s+\d+:\d+\s*$/gmu) || []).length,
      alignment: alignmentProgress
    }
  };
}

async function invalidateStatusForEdit(bookId, stage) {
  const book = resolveBook(bookId);
  const { slug } = lbfHome(book);
  const ledger = await readFile(statusFile, "utf8");
  const result = invalidateAfterEdit(ledger, { book: slug, stage });
  if (result.text !== ledger) await writeFile(statusFile, result.text, "utf8");
  return result.row;
}

function parseMorphLine(line) {
  const match = line.match(/^(\d{6})\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.+)$/u);
  if (!match) return null;
  const [, verseId, partOfSpeech, parsing, surfaceWithPunctuation, surfaceForm, normalizedForm, lemma] = match;
  return { verseId, partOfSpeech, parsing, surfaceWithPunctuation, surfaceForm, normalizedForm, lemma };
}

function formatRmac(partOfSpeech, parsing) {
  return `${partOfSpeech}${String(parsing || "").replace(/^-+/u, "").replace(/-+$/u, "")}`;
}

function parseVerbMorph(parsing = "") {
  const raw = String(parsing || "").replace(/-/gu, "");
  if (!raw) return null;

  // MorphGNT finite verbs appear as either:
  //   1API-S--  → person + tense + voice + mood + number
  //   AAI-3S--  → tense + voice + mood + person + number
  if (/^[123][PIFARL]/u.test(raw)) {
    return {
      person: raw[0],
      tense: raw[1],
      voice: raw[2],
      mood: raw[3],
      number: raw[4] || ""
    };
  }
  if (/^[PIFARL][AMPEONQX]/u.test(raw)) {
    return {
      tense: raw[0],
      voice: raw[1],
      mood: raw[2],
      person: raw[3] || "",
      number: raw[4] || ""
    };
  }
  return null;
}

function describeMorphologySpanish(partOfSpeech, parsing) {
  const compact = String(parsing || "").replace(/-/gu, "");
  const caseNames = { N: "nominativo", G: "genitivo", D: "dativo", A: "acusativo", V: "vocativo" };
  const numberNames = { S: "singular", P: "plural" };
  const genderNames = { M: "masculino", F: "femenino", N: "neutro" };
  const tenseNames = { P: "presente", I: "imperfecto", F: "futuro", A: "aoristo", R: "perfecto", L: "pluscuamperfecto" };
  const voiceNames = { A: "activo", M: "medio", P: "pasivo", E: "medio/pasivo", D: "medio", O: "pasivo", N: "medio/pasivo" };
  const moodNames = { I: "indicativo", S: "subjuntivo", O: "optativo", M: "imperativo", N: "infinitivo", P: "participio", D: "imperativo" };

  if (partOfSpeech === "V-" || String(partOfSpeech).startsWith("V")) {
    const verb = parseVerbMorph(parsing);
    if (!verb) return "—";
    return [
      tenseNames[verb.tense],
      voiceNames[verb.voice],
      moodNames[verb.mood],
      verb.person ? `${verb.person}.ª persona` : "",
      numberNames[verb.number]
    ].filter(Boolean).join(", ") || "—";
  }

  const caseCode = compact.match(/[NGDAV]/u)?.[0];
  const numberCode = compact.match(/[SP]/u)?.[0];
  const genderCode = compact.match(/[MFN]/u)?.[0];
  const description = [caseNames[caseCode], numberNames[numberCode], genderNames[genderCode]].filter(Boolean).join(" ");
  return description || "—";
}

function knownStrongForLemma(lemma) {
  return {
    δοῦλος: "G1401",
    ἀπόστολος: "G652",
    πίστις: "G4102",
    πίστιν: "G4102"
  }[lemma] || "";
}

function formatGreekVerse(rows) {
  return rows
    .map(row => row.surfaceWithPunctuation)
    .join(" ")
    .replace(/\s+([,.;·:!?])/gu, "$1")
    .replace(/\s+([)\]])/gu, "$1")
    .replace(/([([])\s+/gu, "$1")
    .trim();
}

function titusSourceTokenId(chapter, verse, position) {
  return `n56${String(chapter).padStart(3, "0")}${String(verse).padStart(3, "0")}${String(position).padStart(3, "0")}`;
}

function titusSourceTokenRange(chapter, verse, start, end) {
  return Array.from({ length: end - start + 1 }, (_, index) => titusSourceTokenId(chapter, verse, start + index));
}

const knownPhraseTokenIds = new Map([
  ["Titus 1:1|0", titusSourceTokenRange(1, 1, 1, 3)],
  ["Titus 1:1|1", titusSourceTokenRange(1, 1, 4, 7)],
  ["Titus 1:1|2", titusSourceTokenRange(1, 1, 8, 11)],
  ["Titus 1:1|3", titusSourceTokenRange(1, 1, 12, 14)],
  ["Titus 1:1|4", titusSourceTokenRange(1, 1, 15, 17)]
]);

function splitReferenceTokens(text) {
  return String(text || "")
    .trim()
    .split(/\s+/u)
    .map(token => token.replace(/^[,.;:!?¿¡]+|[,.;:!?¿¡]+$/gu, ""))
    .filter(Boolean);
}

function bleGlossToText(es) {
  const core = String(es || "").trim();
  if (!core || core === "?") return "";
  if (!core.includes("·")) return core;

  const parts = [];
  for (const raw of core.split("·")) {
    const part = raw.trim();
    if (!part) continue;
    parts.push(...(bleGlossSplits[part.toLowerCase()] || [part]));
  }

  let out = "";
  for (const part of parts) {
    if (bleGlossBulletMarks.has(part.toLowerCase())) {
      out += `${part}•`;
    } else {
      if (out && !out.endsWith("•")) out += " ";
      out += part;
    }
  }
  return out;
}

async function loadBleTokenGlossIndex(book = "tito") {
  if (bleTokenGlossIndexPromise) return bleTokenGlossIndexPromise;

  bleTokenGlossIndexPromise = (async () => {
    const index = new Map();
    const content = await readFirstExistingFile([
      join(mnaInterlinearDir, `${book}.tokens.jsonl`),
      join(getCgvDataPath(), "datasets", "interlinear", "NT", `${book}.tokens.jsonl`)
    ]);
    if (!content) return index;

    for (const line of content.replace(/\r\n/g, "\n").split("\n")) {
      if (!line.trim()) continue;
      let row;
      try {
        row = JSON.parse(line);
      } catch {
        continue;
      }
      if (!row?.ch || !row?.vs || !row?.tok) continue;
      index.set(`${Number(row.ch)}|${Number(row.vs)}|${Number(row.tok)}`, bleGlossToText(row.es || ""));
    }
    return index;
  })();

  return bleTokenGlossIndexPromise;
}

function buildTokenRows(rows, chapter, verse, bleText, translationIndexes, bleGlossIndex = null) {
  const bleTokens = splitReferenceTokens(bleText);
  return rows.map((row, index) => {
    const sourceTokenId = titusSourceTokenId(chapter, verse, index + 1);
    const glossKey = `${Number(chapter)}|${Number(verse)}|${index + 1}`;
    const bleFromJsonl = bleGlossIndex?.get(glossKey) || "";
    return {
      sourceTokenId,
      greek: row.surfaceForm,
      lemma: row.lemma,
      strongs: knownStrongForLemma(row.lemma),
      rmac: formatRmac(row.partOfSpeech, row.parsing),
      morphology: describeMorphologySpanish(row.partOfSpeech, row.parsing),
      ble: bleFromJsonl || bleTokens[index] || "",
      rv1909: resolveAlignedSpan(translationIndexes, [sourceTokenId])
    };
  });
}

async function loadTitusTranslationUnits() {
  const cgvDataDir = getCgvDataPath();
  const [translationIndexes, bleGlossIndex, bleContent, morphContent] = await Promise.all([
    loadTranslationIndexes(cgvDataDir),
    loadBleTokenGlossIndex("tito"),
    readFirstExistingFile([
      join(cgvDataDir, "bibles/BLE/tito.ble.md"),
      join(bibliaBleOutputDir, "tito.ble.md")
    ]),
    readFirstExistingFile([
      join(cgvDataDir, "morphology/MorphGNT/77-Tit-morphgnt.txt"),
      join(cgvDataDir, "SOURCES/MorphGNT/77-Tit-morphgnt.txt"),
      join(mnaMorphgntDir, "77-Tit-morphgnt.txt")
    ])
  ]);
  const greekByReference = new Map();

  for (const line of morphContent.replace(/\r\n/g, "\n").split("\n")) {
    const row = parseMorphLine(line);
    if (!row) continue;
    const chapter = Number(row.verseId.slice(2, 4));
    const verse = Number(row.verseId.slice(4, 6));
    const reference = `Titus ${chapter}:${verse}`;
    if (!greekByReference.has(reference)) greekByReference.set(reference, []);
    greekByReference.get(reference).push(row);
  }

  return bleContent
    .replace(/\r\n/g, "\n")
    .split("\n")
    .map(line => {
      const match = line.match(/^Tito\s+(\d+):(\d+)\s+(.+)$/u);
      if (!match) return null;
      const [, chapter, verse, bleText] = match;
      const reference = `Titus ${Number(chapter)}:${Number(verse)}`;
      const greekRows = greekByReference.get(reference) || [];
      const sourceTokenIds = greekRows
        .map((_, index) => titusSourceTokenId(Number(chapter), Number(verse), index + 1));
      const tokenRows = buildTokenRows(
        greekRows,
        Number(chapter),
        Number(verse),
        bleText.trim(),
        translationIndexes,
        bleGlossIndex
      );
      const alignedBleText = tokenRows.map(row => row.ble).filter(Boolean).join(" ");
      return {
        reference,
        greekText: formatGreekVerse(greekRows),
        sourceTokenIds,
        tokenRows,
        rv1909Text: translationIndexes.rv1909.get(`17|${Number(chapter)}|${Number(verse)}`)
          || resolveAlignedSpan(translationIndexes, sourceTokenIds),
        bleText: alignedBleText || bleText.trim()
      };
    })
    .filter(Boolean);
}

async function enrichTranslationPhraseRecords(phrases, bookId = "titus") {
  const book = findBook(bookId) || findBook("titus");
  const [loaded, translationIndexes] = await Promise.all([
    loadNtBookUnits(rootDir, bookId).catch(() => ({ units: [] })),
    loadTranslationIndexes(getCgvDataPath()).catch(() => null)
  ]);
  const units = loaded.units || loaded || [];
  const unitsByReference = new Map(units.map(unit => [unit.reference, unit]));
  const isOshb = book?.spine === "oshb";
  const aquiferBook = book?.number != null ? String(book.number).padStart(2, "0") : "";

  return phrases.map(phrase => {
    const unit = unitsByReference.get(phrase.reference);
    if (!unit) return phrase;
    const tokenIds = phrase.sourceTokenIds.length
      ? phrase.sourceTokenIds
      : (knownPhraseTokenIds.get(`${phrase.reference}|${phrase.phraseIndex}`) || unit.sourceTokenIds || []);
    const tokenIdSet = new Set(tokenIds);
    let tokenRows = (unit.tokenRows || []).filter(row => tokenIdSet.has(row.sourceTokenId));
    // Keep TR phrase rows when enrichment filter misses (partial remap / TR-only tokens).
    if (!tokenRows.length && Array.isArray(phrase.tokenRows) && phrase.tokenRows.length) {
      tokenRows = phrase.tokenRows;
    }
    const greekFromTokens = tokenRows.map(row => row.greek).filter(Boolean).join(" ");
    const rv1909TokenText = tokenRows.map(row => row.rv1909).filter(Boolean).join(" ");
    const bleTokenText = tokenRows.map(row => row.ble).filter(Boolean).join(" ");

    let rv1909Text = "";
    if (isOshb && translationIndexes && aquiferBook) {
      const chapter = Number(phrase.chapter || unit.chapter);
      const verse = Number(phrase.verse || unit.verse);
      rv1909Text = lookupRv1909AquiferVerse(translationIndexes, aquiferBook, chapter, verse)
        || unit.rv1909Text
        || "";
    } else if (translationIndexes) {
      rv1909Text = resolveAlignedSpan(translationIndexes, tokenIds)
        || rv1909TokenText
        || phrase.rv1909Text
        || "";
    } else {
      rv1909Text = rv1909TokenText || phrase.rv1909Text || "";
    }

    return {
      ...phrase,
      greek: greekFromTokens || phrase.greek || phrase.hebrew || "",
      sourceTokenIds: tokenIds,
      tokenRows,
      rv1909Text,
      bleText: bleTokenText || phrase.bleText || "",
      suggestionSource: phrase.suggestionSource || (phrase.spanish?.trim() ? "lbf-preliminary" : "blank"),
      textualBasis: phrase.textualBasis || unit.textualBasis || ""
    };
  });
}

const decisionDefaults = {
  status: "Draft",
  version: "1.0",
  effectiveDate: "",
  lemma: "δοῦλος",
  strongs: "G1401",
  preferredRendering: "",
  confidence: "Medium",
  reason: "",
  scope: "",
  scopeReference: "",
  scopeCondition: "",
  approvalAuthority: "",
  approvedBy: "",
  approvedAt: ""
};

function normalizeDecisionValue(value) {
  return String(value || "").trim();
}

function valueOrDash(value) {
  return normalizeDecisionValue(value) || "—";
}

function defaultDecisionMarkdown() {
  return serializeDecisionVersions([decisionDefaults]);
}

function parseDecisionVersions(markdown) {
  const normalized = markdown.replace(/\r\n/g, "\n");
  const matches = [...normalized.matchAll(/^## Version (.+)$/gmu)];
  if (!matches.length) return [];

  return matches.map((match, index) => {
    const start = match.index;
    const end = matches[index + 1]?.index ?? normalized.length;
    const block = normalized.slice(start, end).trim();
    const readField = label => {
      const fieldMatch = block.match(new RegExp(`^${label}:\\s*(.*)$`, "mu"));
      const value = fieldMatch?.[1]?.trim() || "";
      return value === "—" ? "" : value;
    };
    const reasonMatch = block.match(/^### Reason\s*\n([\s\S]*)$/mu);
    const reason = reasonMatch?.[1]
      ?.replace(/\n---\s*$/u, "")
      .trim() || "";

    return {
      status: readField("Status") || "Draft",
      version: readField("Version") || match[1].trim(),
      effectiveDate: readField("Effective Date"),
      lemma: readField("Lemma"),
      strongs: readField("Strong's"),
      preferredRendering: readField("Preferred Rendering"),
      confidence: readField("Confidence") || "Medium",
      scope: readField("Scope"),
      scopeReference: readField("Scope Reference"),
      scopeCondition: readField("Scope Condition"),
      approvalAuthority: readField("Approval Authority"),
      approvedBy: readField("Approved By"),
      approvedAt: readField("Approved At"),
      reason
    };
  });
}

function serializeDecisionVersions(versions) {
  const content = versions.map(version => `## Version ${version.version}

Status: ${valueOrDash(version.status)}
Version: ${valueOrDash(version.version)}
Effective Date: ${valueOrDash(version.effectiveDate)}
Lemma: ${valueOrDash(version.lemma)}
Strong's: ${valueOrDash(version.strongs)}
Preferred Rendering: ${valueOrDash(version.preferredRendering)}
Confidence: ${valueOrDash(version.confidence)}
Scope: ${valueOrDash(version.scope)}
Scope Reference: ${valueOrDash(version.scopeReference)}
Scope Condition: ${valueOrDash(version.scopeCondition)}
Approval Authority: ${valueOrDash(version.approvalAuthority)}
Approved By: ${valueOrDash(version.approvedBy)}
Approved At: ${valueOrDash(version.approvedAt)}

### Reason

${normalizeDecisionValue(version.reason)}
`).join("\n---\n\n");

  return `# Decision

${content}`;
}

function nextDecisionVersion(version) {
  const major = Number.parseInt(String(version || "1.0").split(".")[0], 10);
  return `${Number.isFinite(major) ? major + 1 : 2}.0`;
}

function sameDecisionContent(left, right) {
  return [
    "effectiveDate",
    "lemma",
    "strongs",
    "preferredRendering",
    "confidence",
    "scope",
    "scopeReference",
    "scopeCondition",
    "reason"
  ].every(key => normalizeDecisionValue(left[key]) === normalizeDecisionValue(right[key]));
}

async function readDecisionFile(filePath) {
  const content = await readFile(filePath, "utf8").catch(() => "");
  return content || defaultDecisionMarkdown();
}

async function appendHistory(investigationDir, entry) {
  await appendFile(
    join(investigationDir, "history.md"),
    `\n## ${todayIsoDate()}\n\n${entry}\n`,
    "utf8"
  );
}

function decisionFromBody(body, fallback) {
  return {
    ...fallback,
    status: body.status === "Under Review" ? "Under Review" : "Draft",
    version: fallback.version,
    effectiveDate: normalizeDecisionValue(body.effectiveDate),
    lemma: fallback.lemma || decisionDefaults.lemma,
    strongs: fallback.strongs || decisionDefaults.strongs,
    preferredRendering: normalizeDecisionValue(body.preferredRendering),
    confidence: ["High", "Medium", "Low"].includes(body.confidence) ? body.confidence : "Medium",
    scope: ["Occurrence", "Construction", "Book Default"].includes(body.scope) ? body.scope : "",
    scopeReference: normalizeDecisionValue(body.scopeReference),
    scopeCondition: normalizeDecisionValue(body.scopeCondition),
    reason: normalizeDecisionValue(body.reason),
    approvalAuthority: normalizeDecisionValue(fallback.approvalAuthority),
    approvedBy: normalizeDecisionValue(fallback.approvedBy),
    approvedAt: normalizeDecisionValue(fallback.approvedAt)
  };
}

async function handleDecision(request, response, id) {
  const investigationDir = safeInvestigationPath(id);
  const filePath = join(investigationDir, "decision.md");

  if (request.method === "GET") {
    const content = await readDecisionFile(filePath);
    const versions = parseDecisionVersions(content);
    sendJson(response, 200, {
      decision: versions.at(-1) || decisionDefaults,
      versions,
      content
    });
    return;
  }

  if (request.method !== "PUT") {
    sendJson(response, 405, { error: "Method not allowed" });
    return;
  }

  const body = await readJsonBody(request);
  const existingContent = await readFile(filePath, "utf8").catch(() => "");
  const versions = parseDecisionVersions(existingContent);
  const existingLatest = versions.at(-1) || decisionDefaults;
  let latest = decisionFromBody(body, existingLatest);
  const historyEntries = [];

  if (!versions.length) {
    versions.push(latest);
    historyEntries.push(`Created decision ${latest.version} for ${latest.strongs} ${latest.lemma}.`);
  } else if (existingLatest.status === "Approved" && !sameDecisionContent(existingLatest, latest)) {
    latest = {
      ...latest,
      status: "Draft",
      version: nextDecisionVersion(existingLatest.version),
      effectiveDate: "",
      approvalAuthority: "",
      approvedBy: "",
      approvedAt: ""
    };
    versions.push(latest);
    historyEntries.push(`Revised decision for ${latest.strongs} ${latest.lemma}; created version ${latest.version}.`);
  } else if (existingLatest.status !== "Approved") {
    versions[versions.length - 1] = latest;
  }

  if (body.action === "approve") {
    const current = versions.at(-1);
    if (!normalizeDecisionValue(current.preferredRendering) || !normalizeDecisionValue(current.reason)) {
      sendJson(response, 400, { error: "Preferred Rendering and Reason are required before approval." });
      return;
    }
    if (!["Occurrence", "Construction", "Book Default"].includes(current.scope)) {
      sendJson(response, 400, { error: "Decision Scope is required before approval." });
      return;
    }
    if (current.scope === "Occurrence" && !normalizeDecisionValue(current.scopeReference)) {
      sendJson(response, 400, { error: "Occurrence scope requires Scope Reference." });
      return;
    }
    if (current.scope === "Construction" && !normalizeDecisionValue(current.scopeCondition)) {
      sendJson(response, 400, { error: "Construction scope requires Scope Condition." });
      return;
    }
    const approvedBy = normalizeDecisionValue(body.approvedBy);
    if (body.humanConfirmation !== true || !approvedBy) {
      sendJson(response, 400, { error: "Explicit human confirmation and approver name are required before approval." });
      return;
    }
    if (approvedBy.length > 120) {
      sendJson(response, 400, { error: "Approver name is too long." });
      return;
    }

    const previousApproved = versions.slice(0, -1).filter(version => version.status === "Approved");
    for (const version of previousApproved) {
      version.status = "Superseded";
      historyEntries.push(`Superseded decision ${version.version} for ${version.strongs} ${version.lemma}.`);
    }

    const alreadyApproved = current.status === "Approved";
    current.status = "Approved";
    current.effectiveDate = current.effectiveDate || todayIsoDate();
    current.approvalAuthority = "human";
    current.approvedBy = approvedBy;
    current.approvedAt = new Date().toISOString();
    if (alreadyApproved) {
      historyEntries.push(`Recorded human approval for decision ${current.version} by ${approvedBy}.`);
    } else {
      historyEntries.push(`Approved decision ${current.version} for ${current.strongs} ${current.lemma} by ${approvedBy}.`);
    }
  }

  await writeFile(filePath, serializeDecisionVersions(versions), "utf8");
  for (const entry of historyEntries) {
    await appendHistory(investigationDir, entry);
  }

  sendJson(response, 200, {
    saved: true,
    decision: versions.at(-1),
    versions
  });
}

function occurrenceSourceText(occurrence) {
  return occurrence?.sourceText
    || occurrence?.hebrewText
    || occurrence?.greekText
    || "";
}

function isOtOccurrenceReport(report) {
  return report?.corpus === "OT"
    || report?.language === "hebrew"
    || /^[HA]\d+/i.test(String(report?.strongs || ""));
}

function formatHistoricalWitnesses(occurrence) {
  const translations = occurrence?.translations || {};
  const focus = occurrence?.historicalFocus || {};
  const rows = [
    ["RV1862", "rv1862"],
    ["RV1909", "rv1909"],
    ["SPNBES", "spnbes"],
    ["SPNVBL", "spnvbl"]
  ];
  return rows.map(([label, key]) => {
    const witness = valueOrDash(translations[key]);
    const linked = normalizeDecisionValue(focus[key]);
    const linkStatus = linked
      ? `Recorded source-word link: **${linked}**`
      : "Recorded source-word link: none — no highlight applied; inventing an alignment is prohibited.";
    return `${label}: ${witness}  \n${linkStatus}`;
  }).join("\n\n");
}

function formatOccurrenceEvidence(report, generatedAt) {
  const ot = isOtOccurrenceReport(report);
  const countBy = (items, getKey) => {
    const counts = new Map();
    for (const item of items) {
      const key = valueOrDash(getKey(item));
      counts.set(key, (counts.get(key) || 0) + 1);
    }
    return [...counts.entries()].map(([label, count]) => ({ label, count }));
  };
  const countTable = (headers, rows) => {
    const alignment = headers.map((_, index) => index === headers.length - 1 ? "------:" : "------");
    const body = rows.map(row => `| ${row.map(valueOrDash).join(" | ")} |`).join("\n");
    return [
      `| ${headers.join(" | ")} |`,
      `|${alignment.map(value => ` ${value} `).join("|")}|`,
      body || `| ${headers.map((_, index) => index === headers.length - 1 ? "0" : "—").join(" | ")} |`
    ].join("\n");
  };
  const sortedCounts = counts => [...counts].sort((left, right) => (
    right.count - left.count || left.label.localeCompare(right.label, "el")
  ));
  const morphDescription = () => "—";
  const firstReference = predicate => report.occurrences.find(predicate)?.reference || "—";

  const formRows = sortedCounts(countBy(report.occurrences, occurrence => occurrence.surfaceForm))
    .map(row => [row.label, row.count]);
  const morphologyRows = sortedCounts(countBy(report.occurrences, occurrence => occurrence.morphology))
    .map(row => [row.label, morphDescription(row.label), row.count]);
  const distributionRows = countBy(report.occurrences, occurrence => occurrence.author || occurrence.bookName)
    .map(row => [row.label, row.count]);
  const firstHit = report.occurrences[0]?.reference || "—";
  const firstPauline = firstReference(occurrence => occurrence.author === "Paul");
  const firstTitus = firstReference(occurrence => occurrence.bookName === "Titus");
  const firstDaniel = firstReference(occurrence => occurrence.bookName === "Daniel");
  const contextHeading = ot ? "Hebrew/Aramaic Context" : "Greek Context";
  const morphHeader = ot ? "Morph" : "RMAC";

  const occurrenceSections = report.occurrences.map(occurrence => {
    const translations = occurrence.translations || {};

    return `<details>
<summary>${occurrence.reference}</summary>

#### Reference

${valueOrDash(occurrence.reference)}

#### ${contextHeading}

${valueOrDash(occurrenceSourceText(occurrence))}

#### Morphology

Surface form: ${valueOrDash(occurrence.surfaceForm)}  
Lemma: ${valueOrDash(occurrence.lemma)}  
Strong's: ${valueOrDash(occurrence.strongs)}  
${morphHeader}: ${valueOrDash(occurrence.morphology)}

#### Project

Literal: ${valueOrDash(translations.projectLiteral || occurrence.gloss)}

BLE: ${valueOrDash(translations.ble)}

#### Historical Witnesses

${formatHistoricalWitnesses(occurrence)}

</details>`;
  }).join("\n\n");

  const firstUses = ot
    ? `First OT occurrence: ${firstHit}

First occurrence in Daniel: ${firstDaniel}`
    : `First NT occurrence: ${firstHit}

First Pauline occurrence: ${firstPauline}

First occurrence in Titus: ${firstTitus}`;

  return `# Lemma Profile v0.1 — ${report.subject}

## Lemma Summary

| Field | Value |
|------|-------|
| Lemma | ${valueOrDash(report.lemma)} |
| Strong's | ${valueOrDash(report.strongs)} |
| Total ${ot ? "OT" : "NT"} occurrences | ${report.occurrences.length} |
| Source | cgv-data |
| Generated timestamp | ${generatedAt} |

## Forms Found

${countTable(["Form", "Count"], formRows)}

## Morphology Summary

${countTable([morphHeader, "Description", "Count"], morphologyRows)}

## ${ot ? "Book" : "Author"} Distribution

${countTable([ot ? "Book" : "Author / Book", "Count"], distributionRows)}

## First Uses

${firstUses}

## Occurrence Blocks

${occurrenceSections}
`;
}

function formatSingleOccurrenceEvidence(report, generatedAt, target = {}) {
  const ot = isOtOccurrenceReport(report);
  const reference = normalizeDecisionValue(target.reference);
  const surface = normalizeDecisionValue(target.surface);
  const occurrence = report.occurrences.find(item => (
    (!reference || item.reference === reference)
    && (!surface || item.surfaceForm === surface)
  )) || report.occurrences[0];
  const translations = occurrence?.translations || {};
  const contextHeading = ot ? "Hebrew/Aramaic Context" : "Greek Context";
  const morphHeader = ot ? "Morph" : "RMAC";

  return `# Occurrence Evidence v0.1 — ${valueOrDash(occurrence?.reference)}

## Occurrence Summary

| Field | Value |
|------|-------|
| Reference | ${valueOrDash(occurrence?.reference)} |
| Lemma | ${valueOrDash(occurrence?.lemma || report.lemma)} |
| Strong's | ${valueOrDash(occurrence?.strongs || report.strongs)} |
| Source | cgv-data |
| Generated timestamp | ${generatedAt} |

## ${contextHeading}

${valueOrDash(occurrenceSourceText(occurrence))}

## Morphology

Surface form: ${valueOrDash(occurrence?.surfaceForm)}  
Lemma: ${valueOrDash(occurrence?.lemma)}  
Strong's: ${valueOrDash(occurrence?.strongs)}  
${morphHeader}: ${valueOrDash(occurrence?.morphology)}

## Project

Literal: ${valueOrDash(translations.projectLiteral || occurrence?.gloss)}

BLE: ${valueOrDash(translations.ble)}

## Historical Witnesses

${formatHistoricalWitnesses(occurrence)}
`;
}

function formatConstructionEvidence(report, generatedAt, id) {
  const occurrenceSections = report.occurrences.map(occurrence => {
    const translations = occurrence.translations || {};

    return `### ${occurrence.reference}

Greek:
${valueOrDash(occurrence.greekText)}

Selected form:
${valueOrDash(occurrence.surfaceForm)}

Lemma:
${valueOrDash(occurrence.lemma)}

RMAC:
${valueOrDash(occurrence.morphology)}

BLE:
${valueOrDash(translations.ble)}

RV1909:
${valueOrDash(translations.rv1909)}

RV1862:
—

SPNBES:
—

SPNVBL:
—`;
  }).join("\n\n");

  return `# Construction Evidence — ${valueOrDash(report.construction)}

## Metadata

Investigation: ${valueOrDash(id)}
Reference: ${valueOrDash(report.investigationReference)}
Selected token: ${valueOrDash(report.selectedToken || report.target?.surfaceForm)}
Lemma: ${valueOrDash(report.target?.lemma)}
RMAC: ${valueOrDash(report.selectedRmac)}
Construction: ${valueOrDash(report.construction)}
Search pattern: ${valueOrDash(report.searchPattern)}
Source: cgv-data
Generated at: ${generatedAt}

## Summary

Total matches: ${report.occurrences.length}

## Matches

${occurrenceSections || "No exact construction matches found."}
`;
}

function readMarkdownValue(markdown, heading) {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const headingIndex = lines.findIndex(line => line.trim() === `## ${heading}`);
  if (headingIndex === -1) return "";

  for (let index = headingIndex + 1; index < lines.length; index += 1) {
    const line = lines[index].trim();
    if (!line || line === "---") continue;
    if (line.startsWith("#")) return "";
    return line;
  }

  return "";
}

function readOriginValue(markdown, label) {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n").map(line => line.trim());
  const originIndex = lines.findIndex(line => line === "## Origin");
  if (originIndex === -1) return "";

  const nextSection = lines.findIndex((line, index) => index > originIndex && line.startsWith("## "));
  const end = nextSection === -1 ? lines.length : nextSection;

  for (let index = originIndex + 1; index < end; index += 1) {
    if (lines[index] !== label) continue;
    for (let valueIndex = index + 1; valueIndex < end; valueIndex += 1) {
      const value = lines[valueIndex];
      if (!value || value === "---") continue;
      return value.startsWith("#") ? "" : value;
    }
  }

  return "";
}

async function readInvestigationMeta(id, investigationDir) {
  const readme = await readFile(join(investigationDir, "README.md"), "utf8").catch(() => "");
  return {
    id,
    primarySubject: readMarkdownValue(readme, "Primary Subject"),
    originReference: readOriginValue(readme, "Reference"),
    currentStatus: readMarkdownValue(readme, "Current Status")
  };
}

async function readJsonBody(request) {
  const chunks = [];
  for await (const chunk of request) {
    chunks.push(chunk);
  }
  const raw = Buffer.concat(chunks).toString("utf8");
  return raw ? JSON.parse(raw) : {};
}

async function sendEvidenceMarkdown(response, id, fileName) {
  const investigationDir = safeInvestigationPath(id);
  const evidenceDir = join(investigationDir, "evidence");
  const safeFileName = safeEvidenceFile(decodeURIComponent(fileName));
  const content = await readFile(join(evidenceDir, safeFileName), "utf8").catch(() => "");
  if (!content) {
    send(response, 404, "Not found");
    return;
  }
  const contentType = safeFileName.endsWith(".json")
    ? "application/json; charset=utf-8"
    : "text/markdown; charset=utf-8";
  send(response, 200, content, contentType);
}

async function handleTranslation(request, response, url) {
  if (request.method === "GET") {
    const bookId = bookIdFromRequest(url);
    const { book, phraseFile, documentFile, textualBasis } = await resolvePhraseFile(bookId);
    const [content, phraseContent] = await Promise.all([
      readFile(documentFile, "utf8").catch(() => ""),
      readFile(phraseFile, "utf8").catch(() => "")
    ]);
    let phrases = [];
    if (phraseContent) {
      try {
        phrases = normalizeTranslationPhrases(JSON.parse(phraseContent));
      } catch {
        phrases = [];
      }
    }
    phrases = await enrichTranslationPhraseRecords(phrases, bookId);
    sendJson(response, 200, {
      book: book.id,
      label: book.label,
      bleSlug: book.bleSlug,
      textualBasis,
      reference: phrases[0]?.reference || `${book.label} 1:1`,
      content,
      phrases
    });
    return;
  }

  if (request.method === "PUT" || request.method === "POST") {
    const body = await readJsonBody(request);
    const bookId = bookIdFromRequest(url, body);
    const { book, phraseFile, documentFile, textualBasis } = await resolvePhraseFile(bookId);
    const content = typeof body.content === "string" ? body.content : "";
    const nextContent = content.endsWith("\n") ? content : `${content}\n`;
    const previousContent = await readFile(documentFile, "utf8").catch(() => "");
    const incoming = normalizeTranslationPhrases(body.phrases);
    const existing = await readExistingTranslationPhrases(phraseFile);
    const merged = mergeTranslationPhraseSaves(incoming, existing);
    const phrases = await enrichTranslationPhraseRecords(merged, bookId);
    await mkdir(dirname(documentFile), { recursive: true });
    await mkdir(dirname(phraseFile), { recursive: true });
    await writeFile(documentFile, nextContent, "utf8");
    if (nextContent !== previousContent) {
      await invalidateStatusForEdit(bookId, "translation");
    }
    await writeTranslationPhrases(phraseFile, phrases, book, textualBasis);
    sendJson(response, 200, {
      saved: true,
      book: book.id,
      textualBasis,
      reference: phrases[0]?.reference || `${book.label} 1:1`,
      phraseCount: phrases.length
    });
    return;
  }

  sendJson(response, 405, { error: "Method not allowed" });
}

async function handleReader(request, response, url) {
  if (request.method === "GET" && url.pathname === "/api/reader/books") {
    const books = [];
    for (const book of allTranslatorBooks().filter(item => Number(item.number) < 40)) {
      const { slug, testament } = lbfHome(book);
      const path = join(repoRoot, "translation", testament, `${slug}.md`);
      const content = await readFile(path, "utf8").catch(() => "");
      if (content) books.push({ id: book.id, slug, label: book.label });
    }
    sendJson(response, 200, { books });
    return;
  }

  if (request.method === "GET" && url.pathname === "/api/reader/book") {
    const bookId = bookIdFromRequest(url);
    const book = resolveBook(bookId);
    if (Number(book.number) >= 40) {
      sendJson(response, 400, { error: "The reader currently covers the Old Testament." });
      return;
    }
    const { documentFile } = translationPathsForBook(book.id);
    const content = await readFile(documentFile, "utf8");
    const verses = parseTranslationBook(content).map(({ chapter, verse, text }) => ({ chapter, verse, text }));
    sendJson(response, 200, { book: book.id, label: book.label, verses });
    return;
  }

  if (request.method === "PUT" && url.pathname === "/api/reader/verse") {
    const body = await readJsonBody(request);
    const bookId = bookIdFromRequest(url, body);
    const book = resolveBook(bookId);
    if (Number(book.number) >= 40) {
      sendJson(response, 400, { error: "The reader currently covers the Old Testament." });
      return;
    }
    const { documentFile } = translationPathsForBook(book.id);
    const content = await readFile(documentFile, "utf8");
    let next;
    try {
      next = replaceTranslationVerse(content, body);
    } catch (error) {
      sendJson(response, 409, { error: error.message });
      return;
    }
    if (next !== content) {
      await writeFile(documentFile, next, "utf8");
      await invalidateStatusForEdit(book.id, "translation");
    }
    sendJson(response, 200, { saved: true, chapter: Number(body.chapter), verse: Number(body.verse) });
    return;
  }

  sendJson(response, 405, { error: "Method not allowed" });
}

async function handleReverseLinks(request, response, url) {
  const bookId = bookIdFromRequest(url);
  const paths = translationPathsForBook(bookId);
  const fallbackBasis = paths.book.spine === "oshb" ? "OSHB/WLC" : "Scrivener 1894 TR";

  if (request.method === "GET") {
    try {
      const raw = await readFile(paths.reverseLinksFile, "utf8");
      const doc = JSON.parse(raw);
      sendJson(response, 200, {
        bookId: paths.book.id,
        textualBasis: doc.textualBasis || fallbackBasis,
        schemaVersion: doc.schemaVersion || 1,
        stats: doc.stats || {},
        links: Array.isArray(doc.links) ? doc.links : []
      });
    } catch {
      sendJson(response, 200, {
        bookId: paths.book.id,
        textualBasis: fallbackBasis,
        schemaVersion: 1,
        stats: {},
        links: []
      });
    }
    return;
  }

  if (request.method !== "PUT") {
    sendJson(response, 405, { error: "Method not allowed" });
    return;
  }

  const body = await readJsonBody(request);
  const reference = String(body.reference || "").trim();
  const unitId = String(body.unitId || "").trim();
  const phraseIndex = Number(body.phraseIndex);
  const confirmPhrase = body.confirmPhrase === true;
  const sourceTokenIds = Array.isArray(body.sourceTokenIds)
    ? [...new Set(body.sourceTokenIds.map(String).filter(Boolean))]
    : [];
  if (!reference || (confirmPhrase && !Number.isInteger(phraseIndex)) || (!confirmPhrase && (!unitId || !sourceTokenIds.length))) {
    sendJson(response, 400, {
      error: confirmPhrase
        ? "reference and phraseIndex are required."
        : "reference, unitId, and at least one source token are required."
    });
    return;
  }

  const currentWorkflow = await readBookWorkflow(bookId);
  if (currentWorkflow.row.translation !== "done") {
    sendJson(response, 409, { error: "Approve the translation before editing alignment." });
    return;
  }

  let doc;
  try {
    doc = JSON.parse(await readFile(paths.reverseLinksFile, "utf8"));
  } catch {
    sendJson(response, 409, { error: "This book has no reverse-link document to edit yet." });
    return;
  }

  const link = (doc.links || []).find(item =>
    (Number.isInteger(phraseIndex) && Number(item.phraseIndex) === phraseIndex)
    || String(item.reference || "") === reference
  );
  const unit = (link?.units || []).find(item => String(item.unitId || "") === unitId);
  if (!link || (!confirmPhrase && !unit)) {
    sendJson(response, 404, {
      error: confirmPhrase
        ? `Alignment phrase not found: ${reference}`
        : `Alignment unit not found: ${reference} / ${unitId}`
    });
    return;
  }
  const unitsToValidate = confirmPhrase ? (link.units || []) : [unit];
  if (!unitsToValidate.length || (confirmPhrase && unitsToValidate.some(item => !(item.sourceTokenIds || []).length))) {
    sendJson(response, 409, { error: "Every unit in the phrase must have source tokens before confirmation." });
    return;
  }

  const tokenVerse = await loadSourceTokenVerseIndex(paths);
  if (!tokenVerse?.size) {
    sendJson(response, 409, { error: "The canonical source-token spine is missing." });
    return;
  }
  const cv = String(link.mtReference || link.reference || "").match(/(\d+:\d+)\s*$/u)?.[1] || "";
  const validatedTokenIds = confirmPhrase
    ? unitsToValidate.flatMap(item => (item.sourceTokenIds || []).map(String))
    : sourceTokenIds;
  const unknown = validatedTokenIds.filter(id => !tokenVerse.has(id));
  const wrongVerse = validatedTokenIds.filter(id => tokenVerse.has(id) && tokenVerse.get(id) !== cv);
  if (unknown.length || wrongVerse.length) {
    sendJson(response, 400, {
      error: unknown.length
        ? `Unknown source token IDs: ${unknown.join(", ")}`
        : `Source token IDs outside ${cv}: ${wrongVerse.join(", ")}`
    });
    return;
  }

  const previous = (unit?.sourceTokenIds || []).map(String);
  const changed = confirmPhrase
    ? link.status !== "hand"
      || unitsToValidate.some(item => !["hand", "manual", "manual-realign"].includes(item.method))
    : JSON.stringify(previous) !== JSON.stringify(sourceTokenIds) || unit.method !== "hand";
  if (changed) {
    if (confirmPhrase) {
      for (const item of unitsToValidate) {
        item.method = "hand";
        item.status = "confirmed";
      }
    } else {
      unit.sourceTokenIds = sourceTokenIds;
      unit.method = "hand";
      unit.status = "confirmed";
    }
    // Saving one unit is not approval of the rest of a seeded phrase. Only
    // the explicit whole-phrase confirmation may write link.status = hand.
    link.status = confirmPhrase ? "hand" : "in-progress";
    doc.stats = { ...(doc.stats || {}), ...alignmentMethodCounts(doc) };
    await writeFile(paths.reverseLinksFile, `${JSON.stringify(doc, null, 2)}\n`, "utf8");
    await invalidateStatusForEdit(bookId, "alignment");
  }
  sendJson(response, 200, { saved: true, confirmedPhrase: confirmPhrase, unit, workflow: await readBookWorkflow(bookId) });
}

async function handleBookWorkflow(request, response, url) {
  const bookId = bookIdFromRequest(url);
  if (request.method === "GET") {
    sendJson(response, 200, await readBookWorkflow(bookId));
    return;
  }
  if (request.method !== "POST") {
    sendJson(response, 405, { error: "Method not allowed" });
    return;
  }

  const body = await readJsonBody(request);
  const action = String(body.action || "");
  const current = await readBookWorkflow(bookId);

  if (action === "verify") {
    const stage = String(body.stage || "");
    if (!new Set(["translation", "alignment"]).has(stage)) {
      sendJson(response, 400, { error: "Verification stage must be translation or alignment." });
      return;
    }
    if (stage === "alignment" && current.row.translation !== "done") {
      sendJson(response, 409, { error: "Approve the translation before verifying alignment." });
      return;
    }
    const result = await runCanonicalTool("verify.py", current.slug);
    sendJson(response, result.ok ? 200 : 409, {
      ok: result.ok,
      output: result.output,
      workflow: await readBookWorkflow(bookId)
    });
    return;
  }

  if (action === "approve") {
    if (body.humanConfirmation !== true) {
      sendJson(response, 400, { error: "Explicit human confirmation is required." });
      return;
    }
    const original = await readFile(statusFile, "utf8");
    let approved;
    try {
      approved = approveStage(original, {
        book: current.slug,
        stage: String(body.stage || ""),
        approvedBy: body.approvedBy,
        approvedOn: todayIsoDate()
      });
      await writeFile(statusFile, approved.text, "utf8");
      const check = await runCanonicalTool("status.py", current.slug);
      if (!check.ok) {
        await writeFile(statusFile, original, "utf8");
        sendJson(response, 409, { error: "Approval was not recorded because the canonical status check failed.", output: check.output });
        return;
      }
      sendJson(response, 200, { approved: true, output: check.output, workflow: await readBookWorkflow(bookId) });
    } catch (error) {
      sendJson(response, 409, { error: error.message });
    }
    return;
  }

  if (action === "commit") {
    try {
      const result = await commitFinishedBook(bookId, {
        message: body.message,
        humanConfirmation: body.humanConfirmation
      });
      sendJson(response, 200, { ...result, workflow: await readBookWorkflow(bookId) });
    } catch (error) {
      sendJson(response, 409, {
        error: error.message,
        output: error.output || "",
        workflow: await readBookWorkflow(bookId)
      });
    }
    return;
  }

  if (action === "export") {
    const provenance = await readBookProvenance(bookId);
    if (!provenance.committed) {
      sendJson(response, 409, {
        error: "Review and commit this finished book before exporting it.",
        workflow: await readBookWorkflow(bookId)
      });
      return;
    }
    const result = await runCanonicalTool("export.py", current.slug);
    sendJson(response, result.ok ? 200 : 409, {
      ok: result.ok,
      output: result.output,
      workflow: await readBookWorkflow(bookId)
    });
    return;
  }

  if (action === "publish") {
    if (body.humanConfirmation !== true) {
      sendJson(response, 400, { error: "Explicit human confirmation is required before publishing." });
      return;
    }
    if (current.row.translation !== "done" || current.row.alignment !== "done") {
      sendJson(response, 409, {
        error: "Translation and alignment must both be approved before publishing.",
        workflow: await readBookWorkflow(bookId)
      });
      return;
    }
    const provenance = await readBookProvenance(bookId);
    if (!provenance.committed) {
      sendJson(response, 409, {
        error: "Review and commit this finished book before publishing it.",
        workflow: await readBookWorkflow(bookId)
      });
      return;
    }
    const exported = await readExportState(bookId);
    if (!exported.ready) {
      sendJson(response, 409, {
        error: exported.problem || "Export this book before publishing it.",
        workflow: await readBookWorkflow(bookId)
      });
      return;
    }
    const already = await readLocalPublicationState(current.slug, exported);
    if (already.publishedToMain) {
      sendJson(response, 200, {
        ok: true,
        output: `${current.slug} is already present on cgv-data/main`
          + (already.publishedSourceCommit
            ? ` (sourceCommit ${already.publishedSourceCommit.slice(0, 12)}).`
            : ".")
          + " No new publisher branch is needed.",
        publication: {
          branch: already.branch,
          commit: already.publishedSourceCommit || "",
          dataRepo: already.defaultDataRepo,
          pushCommand: already.pushCommand,
          pullRequestUrl: already.pullRequestUrl,
          alreadyPublished: true
        },
        workflow: await readBookWorkflow(bookId)
      });
      return;
    }
    if (already.localBranchReady && already.branch) {
      sendJson(response, 200, {
        ok: true,
        output: `Publisher branch ${already.branch} already exists in ${already.defaultDataRepo}.\n`
          + "Push it and merge its pull request — do not create it again.\n"
          + `  ${already.pushCommand}\n`
          + `  ${already.pullRequestUrl}`,
        publication: {
          branch: already.branch,
          commit: "",
          dataRepo: already.defaultDataRepo,
          pushCommand: already.pushCommand,
          pullRequestUrl: already.pullRequestUrl,
          alreadyPrepared: true
        },
        workflow: await readBookWorkflow(bookId)
      });
      return;
    }
    const requestedDataRepo = String(body.dataRepo || defaultDataRepo).trim();
    const dataRepo = resolve(repoRoot, requestedDataRepo);
    const result = await runCanonicalPublisher(current.slug, dataRepo);
    const branch = result.output.match(/^branch\s+(\S+)$/mu)?.[1] || "";
    const commit = result.output.match(/^commit\s+([0-9a-f]{40})$/mu)?.[1] || "";
    sendJson(response, result.ok ? 200 : 409, {
      ok: result.ok,
      error: result.ok ? undefined : "The canonical publisher refused to create the branch. Review its output below.",
      output: result.output,
      publication: result.ok ? {
        branch,
        commit,
        dataRepo,
        pushCommand: `git -C ${shellSingleQuote(dataRepo)} push -u origin ${branch}`,
        pullRequestUrl: `https://github.com/Cultivados-en-Gracia-y-Verdad/cgv-data/compare/main...${branch}?expand=1`
      } : null,
      workflow: await readBookWorkflow(bookId)
    });
    return;
  }

  sendJson(response, 400, { error: "Unknown workflow action." });
}

async function readPhrasePipelineBody(request) {
  const body = await readJsonBody(request);
  const book = typeof body.book === "string" ? body.book.trim().toLowerCase() : "";
  const reference = typeof body.reference === "string" ? body.reference.trim() : "";
  const greek = typeof body.greek === "string" ? body.greek.trim() : "";
  const rv1909Text = typeof body.rv1909Text === "string" ? body.rv1909Text : "";
  const bleText = typeof body.bleText === "string" ? body.bleText : "";
  const tokenRows = Array.isArray(body.tokenRows) ? body.tokenRows : [];
  const priorLbf = Array.isArray(body.priorLbf)
    ? body.priorLbf
      .filter(item => item && typeof item.spanish === "string" && item.spanish.trim())
      .map(item => ({
        reference: String(item.reference || ""),
        spanish: String(item.spanish || "").trim()
      }))
    : [];

  return {
    book,
    reference,
    greek: greek || tokenRows.map(row => row.greek).filter(Boolean).join(" "),
    rv1909Text,
    bleText,
    tokenRows,
    priorLbf
  };
}

async function handleTranslationAi(request, response) {
  if (request.method === "GET") {
    sendJson(response, 200, await describeAiAvailability());
    return;
  }
  sendJson(response, 405, { error: "Method not allowed" });
}

async function handleTranslationGates(request, response) {
  if (request.method !== "POST") {
    sendJson(response, 405, { error: "Method not allowed" });
    return;
  }

  const payload = await readPhrasePipelineBody(request);
  if (!payload.reference || (!payload.greek && !payload.tokenRows.length)) {
    sendJson(response, 400, { error: "reference and greek/tokenRows are required" });
    return;
  }

  try {
    const analysis = await analyzePhraseGates({
      rootDir,
      bookId: String(payload.book || "").trim().toLowerCase(),
      reference: payload.reference,
      greek: payload.greek,
      tokenRows: payload.tokenRows,
      rv1909Text: payload.rv1909Text,
      priorLbf: payload.priorLbf
    });
    sendJson(response, 200, analysis);
  } catch (error) {
    sendJson(response, 500, {
      error: error.message || "Gate analysis failed",
      code: "GATE_ANALYSIS_FAILED"
    });
  }
}

async function handleTranslationGatesAssist(request, response) {
  if (request.method !== "POST") {
    sendJson(response, 405, { error: "Method not allowed" });
    return;
  }

  const payload = await readPhrasePipelineBody(request);
  if (!payload.reference || (!payload.greek && !payload.tokenRows.length)) {
    sendJson(response, 400, { error: "reference and greek/tokenRows are required" });
    return;
  }

  try {
    const analysis = await analyzePhraseGates({
      rootDir,
      bookId: String(payload.book || "").trim().toLowerCase(),
      reference: payload.reference,
      greek: payload.greek,
      tokenRows: payload.tokenRows,
      rv1909Text: payload.rv1909Text,
      priorLbf: payload.priorLbf
    });
    const assist = await assistPhraseGates({
      rootDir,
      analysis,
      rv1909Text: payload.rv1909Text
    });
    sendJson(response, 200, { analysis, assist });
  } catch (error) {
    const status = ["AI_NOT_CONFIGURED", "OLLAMA_UNREACHABLE", "LMSTUDIO_UNREACHABLE", "LMSTUDIO_MODEL_MISSING"].includes(error?.code)
      ? 503
      : 502;
    sendJson(response, status, {
      error: error.message || "Gate assist failed",
      code: error.code || "GATE_ASSIST_FAILED"
    });
  }
}

async function handleApi(request, response, url) {
  if (url.pathname === "/api/translation/current") {
    await handleTranslation(request, response, url);
    return;
  }

  if (url.pathname === "/api/workflow") {
    await handleBookWorkflow(request, response, url);
    return;
  }

  if (url.pathname.startsWith("/api/reader/")) {
    await handleReader(request, response, url);
    return;
  }

  if (request.method === "GET" && url.pathname === "/api/translation/books") {
    const books = allTranslatorBooks().map(book => ({
      id: book.id,
      label: book.label,
      bleSlug: book.bleSlug,
      number: book.number,
      hasPhrases: false,
      spine: book.spine || "nt"
    }));
    await Promise.all(books.map(async book => {
      const home = lbfHome(findBook(book.id) || book);
      const alignDir = join(repoRoot, "alignment", home.testament, home.slug);
      const candidates = [
        join(alignDir, `${home.slug}-phrases.json`),
        join(alignDir, `${home.slug}-phrases-tr.json`)
      ];
      for (const candidate of candidates) {
        try {
          await stat(candidate);
          book.hasPhrases = true;
          if (candidate.endsWith("-phrases.json")) {
            book.textualBasis = "OSHB/WLC";
          } else {
            book.textualBasis = "Scrivener 1894 TR";
          }
          break;
        } catch {
          // try next
        }
      }
    }));
    sendJson(response, 200, {
      books,
      active: bookIdFromRequest(url)
    });
    return;
  }

  if (url.pathname === "/api/translation/ai") {
    await handleTranslationAi(request, response);
    return;
  }

  // Compatibility: availability only (single-shot suggest removed).
  if (url.pathname === "/api/translation/suggest") {
    await handleTranslationAi(request, response);
    return;
  }

  if (url.pathname === "/api/translation/gates/assist") {
    await handleTranslationGatesAssist(request, response);
    return;
  }

  if (url.pathname === "/api/translation/gates") {
    await handleTranslationGates(request, response);
    return;
  }

  if (request.method === "GET" && url.pathname === "/api/translation/units") {
    const bookId = bookIdFromRequest(url);
    const book = resolveBook(bookId);
    const loaded = await loadNtBookUnits(rootDir, bookId);
    sendJson(response, 200, { book: book.label, bookId: book.id, units: loaded.units || [] });
    return;
  }

  if (url.pathname === "/api/translation/reverse-links") {
    await handleReverseLinks(request, response, url);
    return;
  }

  if (url.pathname === "/api/investigations") {
    if (request.method === "GET") {
      const bookId = bookIdFromRequest(url);
      const bookDir = join(investigationsDir, bookId);
      const entries = await readdir(bookDir, { withFileTypes: true }).catch(() => []);
      const bookNumber = String(resolveBook(bookId).number).padStart(2, "0");
      const investigations = entries
        .filter(entry => entry.isDirectory() && /^INV-\d{2}-\d{4}$/.test(entry.name))
        .filter(entry => entry.name.startsWith(`INV-${bookNumber}-`))
        .map(entry => entry.name)
        .sort();
      sendJson(response, 200, { book: bookId, investigations });
      return;
    }

    if (request.method === "POST") {
      try {
        const body = await readJsonBody(request);
        const bookId = bookIdFromRequest(url, body);
        const book = resolveBook(bookId);
        const result = await createInvestigationFromLemma(rootDir, {
          ...body,
          book: bookId,
          bookLabel: book.label
        });
        sendJson(response, result.created ? 201 : 200, result);
      } catch (error) {
        sendJson(response, 400, { error: error.message || "Could not create investigation" });
      }
      return;
    }

    sendJson(response, 405, { error: "Method not allowed" });
    return;
  }

  const evidenceMatch = url.pathname.match(/^\/api\/investigations\/(INV-\d{2}-\d{4})\/evidence(?:\/([^/]+))?$/);
  if (evidenceMatch) {
    const [, id, fileName] = evidenceMatch;
    const investigationDir = safeInvestigationPath(id);
    const evidenceDir = join(investigationDir, "evidence");

    if (request.method === "GET" && !fileName) {
      const entries = await readdir(evidenceDir, { withFileTypes: true }).catch(() => []);
      const files = entries
        .filter(entry => entry.isFile() && entry.name.endsWith(".md") && entry.name !== "README.md")
        .map(entry => ({ name: entry.name, path: `evidence/${entry.name}` }))
        .sort((left, right) => left.name.localeCompare(right.name));
      sendJson(response, 200, { id, files });
      return;
    }

    if (request.method === "GET" && fileName) {
      await sendEvidenceMarkdown(response, id, fileName);
      return;
    }

    sendJson(response, 405, { error: "Method not allowed" });
    return;
  }

  const gatherMatch = url.pathname.match(/^\/api\/investigations\/(INV-\d{2}-\d{4})\/gather$/);
  if (gatherMatch) {
    const [, id] = gatherMatch;
    const investigationDir = safeInvestigationPath(id);

    if (request.method !== "POST") {
      sendJson(response, 405, { error: "Method not allowed" });
      return;
    }

    const evidenceDir = join(investigationDir, "evidence");
    const body = await readJsonBody(request);
    const evidenceTypes = {
      occurrence: {
        fileName: "occurrence.md",
        existsMessage: "occurrence.md already exists"
      },
      occurrences: {
        fileName: "occurrences.md",
        existsMessage: "occurrences.md already exists"
      },
      construction: {
        fileName: "construction.md",
        existsMessage: "construction.md already exists"
      }
    };
    const evidenceType = evidenceTypes[body.type];

    if (!evidenceType) {
      sendJson(response, 400, { error: "Only occurrence, lemma, and construction gathering are implemented" });
      return;
    }

    const fileName = evidenceType.fileName;
    const filePath = join(evidenceDir, fileName);
    const exists = await stat(filePath).then(() => true).catch(() => false);

    if (exists && body.replace !== true) {
      sendJson(response, 409, {
        code: "EVIDENCE_EXISTS",
        fileName,
        error: evidenceType.existsMessage
      });
      return;
    }

    const decisionContent = await readFile(join(investigationDir, "decision.md"), "utf8").catch(() => "");
    const decision = parseDecisionVersions(decisionContent).at(-1) || {};
    const meta = await readInvestigationMeta(id, investigationDir);
    const primary = String(meta.primarySubject || "");
    const primaryStrongs = (primary.match(/\b[GHA]\d+\b/i) || [])[0] || "";
    const primaryLemma = primary.replace(/^[GHA]\d+\s*[—-]\s*/iu, "").trim();

    const strongs = normalizeDecisionValue(body.strongs)
      || normalizeDecisionValue(decision.strongs)
      || primaryStrongs;
    const lemma = normalizeDecisionValue(body.lemma)
      || normalizeDecisionValue(decision.lemma)
      || primaryLemma;
    const reference = normalizeDecisionValue(body.reference)
      || normalizeDecisionValue(meta.originReference)
      || "Titus 1:1";
    const surface = normalizeDecisionValue(body.surface);
    const language = languageFromStrongs(strongs, body.language || "");

    if (!strongs && !lemma) {
      sendJson(response, 400, {
        error: "Investigation is missing Strong's and lemma. Set them in Decision before gathering evidence."
      });
      return;
    }

    const generatedAt = new Date().toISOString();
    let evidence = "";
    let historyEntry = "";

    try {
      if (body.type === "construction") {
        if (language === "hebrew") {
          sendJson(response, 400, {
            error: "Construction gathering is Greek-only for now. Use Occurrence or Occurrences for Hebrew/Aramaic."
          });
          return;
        }
        const report = await getGreekConstructionEvidence({
          strongs,
          lemma,
          surface,
          reference,
          rmac: body.rmac,
          prepositionLemma: body.prepositionLemma,
          prepositionSurface: body.prepositionSurface,
          caseCode: body.caseCode
        });
        evidence = formatConstructionEvidence(report, generatedAt, id);
        historyEntry = `Generated Construction Evidence v0.1 for ${report.construction} from cgv-data.`;
      } else {
        const report = language === "hebrew"
          ? await getHebrewOccurrencesByStrongs(strongs, { lemma })
          : await getGreekOccurrencesByStrongs(strongs, { lemma });
        evidence = body.type === "occurrence"
          ? formatSingleOccurrenceEvidence(report, generatedAt, {
            ...body,
            reference,
            surface,
            lemma,
            strongs: report.strongs || strongs
          })
          : formatOccurrenceEvidence(report, generatedAt);
        historyEntry = body.type === "occurrence"
          ? `Generated occurrence evidence for ${report.strongs || strongs} ${report.lemma} from cgv-data.`
          : `Generated Lemma Profile v0.1 occurrence evidence for ${report.strongs || strongs} ${report.lemma} from cgv-data.`;
      }
    } catch (error) {
      sendJson(response, 400, {
        code: error.code || "GATHER_FAILED",
        error: error instanceof Error ? error.message : String(error)
      });
      return;
    }

    await mkdir(evidenceDir, { recursive: true });
    await writeFile(filePath, evidence.endsWith("\n") ? evidence : `${evidence}\n`, "utf8");
    await appendHistory(investigationDir, historyEntry);

    sendJson(response, 200, {
      generated: true,
      replaced: exists,
      file: { name: basename(filePath), path: `evidence/${fileName}` },
      subject: { strongs, lemma, reference }
    });
    return;
  }

  const decisionMatch = url.pathname.match(/^\/api\/investigations\/(INV-\d{2}-\d{4})\/decision$/);
  if (decisionMatch) {
    await handleDecision(request, response, decisionMatch[1]);
    return;
  }

  const match = url.pathname.match(/^\/api\/investigations\/(INV-\d{2}-\d{4})(?:\/files\/([^/]+))?$/);
  if (!match) {
    sendJson(response, 404, { error: "Not found" });
    return;
  }

  const [, id, fileName] = match;
  const investigationDir = safeInvestigationPath(id);

  if (request.method === "GET" && !fileName) {
    const files = await Promise.all(
      tabs.map(async tab => {
        const path = join(investigationDir, tab.file);
        const exists = await stat(path).then(() => true).catch(() => false);
        return { ...tab, exists };
      })
    );
    const meta = await readInvestigationMeta(id, investigationDir);
    sendJson(response, 200, { id, meta, files });
    return;
  }

  if (!fileName) {
    sendJson(response, 405, { error: "Method not allowed" });
    return;
  }

  const tab = safeTabFile(decodeURIComponent(fileName));
  const filePath = join(investigationDir, tab.file);

  if (request.method === "GET") {
    const content = tab.file === "decision.md"
      ? await readDecisionFile(filePath)
      : await readFile(filePath, "utf8").catch(() => "");
    sendJson(response, 200, { id, tab: tab.id, file: tab.file, content });
    return;
  }

  if (request.method === "PUT") {
    const body = await readJsonBody(request);
    const content = typeof body.content === "string" ? body.content : "";
    await writeFile(filePath, content.endsWith("\n") ? content : `${content}\n`, "utf8");
    sendJson(response, 200, { saved: true, id, tab: tab.id, file: tab.file });
    return;
  }

  sendJson(response, 405, { error: "Method not allowed" });
}

async function handleStatic(response, url) {
  const requested = url.pathname === "/" ? "/index.html" : url.pathname;
  const path = normalize(join(publicDir, requested));
  if (!path.startsWith(publicDir)) {
    send(response, 403, "Forbidden");
    return;
  }

  try {
    const content = await readFile(path);
    send(response, 200, content, contentTypes[extname(path)] || "application/octet-stream");
  } catch {
    send(response, 404, "Not found");
  }
}

createServer(async (request, response) => {
  try {
    const url = new URL(request.url || "/", `http://${request.headers.host}`);
    if (url.pathname.startsWith("/api/")) {
      await handleApi(request, response, url);
      return;
    }

    const evidenceAliasMatch = url.pathname.match(/^\/investigations\/(INV-\d{2}-\d{4})\/evidence\/([^/]+)$/);
    if (request.method === "GET" && evidenceAliasMatch) {
      const [, id, fileName] = evidenceAliasMatch;
      await sendEvidenceMarkdown(response, id, fileName);
      return;
    }

    await handleStatic(response, url);
  } catch (error) {
    sendJson(response, 500, { error: error instanceof Error ? error.message : String(error) });
  }
}).listen(port, "127.0.0.1", () => {
  console.log(`CGV Translator prototype: http://127.0.0.1:${port}/`);
});
