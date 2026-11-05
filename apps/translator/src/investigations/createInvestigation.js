import { mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { findBook } from "../data/bookCatalog.js";

function todayIsoDate() {
  return new Date().toLocaleDateString("en-CA", { timeZone: "America/La_Paz" });
}

function hasHebrewScript(value = "") {
  return /[\u0590-\u05FF]/u.test(String(value || ""));
}

/**
 * Normalize Strong's ids for Greek (G) and Hebrew/Aramaic (H).
 * Bare digits default to G unless language is hebrew/aramaic or the lemma/surface is Hebrew script.
 */
export function normalizeStrongs(value = "", { language = "", lemma = "", surface = "" } = {}) {
  const raw = String(value || "").trim().toUpperCase();
  if (!raw) return "";
  const prefixed = raw.match(/^([GHA])(\d+)/);
  if (prefixed) return `${prefixed[1]}${prefixed[2]}`;
  if (/^\d+$/.test(raw)) {
    const lang = String(language || "").toLowerCase();
    const hebrewish = lang === "hebrew" || lang === "aramaic" || lang === "he" || lang === "arc"
      || hasHebrewScript(lemma)
      || hasHebrewScript(surface);
    return `${hebrewish ? "H" : "G"}${raw}`;
  }
  return raw;
}

export function languageFromStrongs(strongs = "", fallback = "") {
  const normalized = String(strongs || "").trim().toUpperCase();
  if (normalized.startsWith("H") || normalized.startsWith("A")) return "hebrew";
  if (normalized.startsWith("G")) return "greek";
  return fallback || "";
}

function sourceLanguageLabel(language = "") {
  if (language === "hebrew" || language === "aramaic" || language === "he" || language === "arc") {
    return "Hebrew/Aramaic";
  }
  return "Greek";
}

function bookFromReference(reference = "") {
  const match = String(reference || "").trim().match(/^(.+?)\s+\d+/u);
  return match ? match[1].trim() : "Titus";
}

const INVESTIGATION_ID_RE = /^INV-(\d{2})-(\d{4})$/;

export function parseInvestigationId(id = "") {
  const match = String(id).match(INVESTIGATION_ID_RE);
  if (!match) return null;
  return {
    bookNumber: Number(match[1]),
    sequence: Number(match[2])
  };
}

export function formatInvestigationId(bookNumber, sequence) {
  const book = Number(bookNumber);
  const item = Number(sequence);
  if (!Number.isInteger(book) || book < 1 || book > 66) {
    throw new Error("canonical book number must be an integer from 1 through 66");
  }
  if (!Number.isInteger(item) || item < 1 || item > 9999) {
    throw new Error("investigation sequence must be an integer from 1 through 9999");
  }
  return `INV-${String(book).padStart(2, "0")}-${String(item).padStart(4, "0")}`;
}

function investigationNumber(id = "") {
  return parseInvestigationId(id)?.sequence || 0;
}

function parseDecisionVersions(markdown) {
  const sections = String(markdown || "").split(/^## Version\s+/m).slice(1);
  return sections.map(section => {
    const lines = section.replace(/\r\n/g, "\n").split("\n");
    const fields = {};
    for (const line of lines) {
      const match = line.match(/^([^:]+):\s*(.*)$/);
      if (!match) continue;
      fields[match[1].trim().toLowerCase()] = match[2].trim();
    }
    return {
      lemma: fields.lemma || "",
      strongs: normalizeStrongs(fields["strong's"] || fields.strongs || "", {
        lemma: fields.lemma || ""
      }),
      status: fields.status || ""
    };
  });
}

function readPrimarySubject(readme = "") {
  const match = String(readme).match(/## Primary Subject\s*\n+([^\n]+)/);
  return (match?.[1] || "").trim();
}

function parsePrimarySubject(primary = "") {
  const text = String(primary || "").trim();
  const strongs = normalizeStrongs((text.match(/\b[GHA]\d+\b/i) || [])[0] || "");
  const lemma = text.replace(/^[GHA]\d+\s*[—-]\s*/iu, "").trim();
  return { strongs, lemma };
}

export async function listInvestigationIds(investigationsDir) {
  const entries = await readdir(investigationsDir, { withFileTypes: true }).catch(() => []);
  return entries
    .filter(entry => entry.isDirectory() && INVESTIGATION_ID_RE.test(entry.name))
    .map(entry => entry.name)
    .sort();
}

export async function allocateNextInvestigationId(bookInvestigationsDir, bookNumber) {
  const canonicalBookNumber = Number(bookNumber);
  const ids = await listInvestigationIds(bookInvestigationsDir);
  const localIds = ids.filter(id => parseInvestigationId(id)?.bookNumber === canonicalBookNumber);
  const next = Math.max(0, ...localIds.map(investigationNumber)) + 1;
  return formatInvestigationId(canonicalBookNumber, next);
}

export async function findInvestigationByLemma(investigationsDir, { lemma = "", strongs = "", language = "" } = {}) {
  const targetLemma = String(lemma || "").trim();
  const targetStrongs = normalizeStrongs(strongs, { language, lemma });
  if (!targetLemma && !targetStrongs) return null;

  const ids = await listInvestigationIds(investigationsDir);
  for (const id of ids) {
    const dir = join(investigationsDir, id);
    const [decisionMd, readme] = await Promise.all([
      readFile(join(dir, "decision.md"), "utf8").catch(() => ""),
      readFile(join(dir, "README.md"), "utf8").catch(() => "")
    ]);
    const latest = parseDecisionVersions(decisionMd).at(-1);
    const primary = parsePrimarySubject(readPrimarySubject(readme));

    const strongsMatch = targetStrongs
      && (latest?.strongs === targetStrongs || primary.strongs === targetStrongs);
    const lemmaMatch = targetLemma
      && (latest?.lemma === targetLemma || primary.lemma === targetLemma);

    if (strongsMatch || lemmaMatch) {
      return {
        id,
        lemma: latest?.lemma || primary.lemma || targetLemma,
        strongs: latest?.strongs || primary.strongs || targetStrongs,
        status: latest?.status || "Draft"
      };
    }
  }

  return null;
}

function buildScaffold({
  id,
  lemma,
  strongs,
  reference,
  clause,
  surface,
  ble,
  book,
  language
}) {
  const date = todayIsoDate();
  const subject = [strongs, lemma].filter(Boolean).join(" — ") || lemma;
  const clauseText = clause || surface || lemma;
  const bleNote = ble || "—";
  const languageLabel = sourceLanguageLabel(language);

  const readme = `# Investigation ${id}

## Origin

Project

LPF

Book

${book}

Reference

${reference}

Clause

${clauseText}

---

## Why this investigation exists

Translation paused because the translator chose to investigate the ${languageLabel} lemma ${lemma}${strongs ? ` (${strongs})` : ""}.

---

## Objective

Determine whether a stable LBF rendering is needed for the primary subject of this investigation.

---

## Final Authority

The biblical text.

---

## Primary Subject

${subject}

---

## Related Subjects

None identified.

---

## Current Status

Observation
`;

  const observations = `# Observations

## Objective

Record only observations that are directly supported by the biblical text.

Do not record conclusions.

Do not establish translation policy.

Questions belong in \`questions.md\`.

---

## Origin Clause

${reference}

> ${clauseText}

---

## Initial Observations

### O-001

The investigation originates from ${reference}.

### O-002

The current provisional rendering is ${bleNote}.
`;

  const decision = `# Decision

## Version 0.1

Status: Draft
Version: 0.1
Effective Date: ${date}
Lemma: ${lemma}
Strong's: ${strongs}
Preferred Rendering: 
Confidence: 
Scope: Occurrence
Scope Reference: ${reference}
Scope Condition:
Approval Authority: 
Approved By: 
Approved At: 

### Reason

Investigation opened; decision not yet made.
`;

  const questions = `# Questions

## Initial Questions

### Q-001

Does ${lemma} require an LBF decision beyond the provisional rendering?
`;

  const evidence = `# Evidence

Evidence has not been gathered yet.
`;

  const research = `# Research

No research notes recorded yet.
`;

  const policy = `# Policy

No policy has been established yet.
`;

  const history = `# History

## ${date}

Investigation ${id} created from ${reference || "translator request"} for ${subject}.
`;

  const evidenceReadme = `# Evidence

## Purpose

This directory contains objective evidence gathered during the investigation.

Evidence should be directly traceable to the biblical text.

Research and interpretation belong elsewhere.

---

## Current Evidence

None yet.

Additional evidence may be added as the investigation requires.
`;

  return {
    "README.md": readme,
    "observations.md": observations,
    "decision.md": decision,
    "questions.md": questions,
    "evidence.md": evidence,
    "research.md": research,
    "policy.md": policy,
    "history.md": history,
    "evidence/README.md": evidenceReadme
  };
}

/**
 * Create a new investigation folder from a lemma, or return an existing match.
 */
export async function createInvestigationFromLemma(rootDir, body = {}) {
  const surface = String(body.surface || "").trim();
  const rawLemma = String(body.lemma || "").trim();
  if (!rawLemma && !surface) {
    throw new Error("lemma is required");
  }

  const languageHint = String(body.language || "").trim().toLowerCase()
    || languageFromStrongs(body.strongs)
    || (hasHebrewScript(rawLemma) || hasHebrewScript(surface) ? "hebrew" : "greek");

  const strongs = normalizeStrongs(body.strongs, {
    language: languageHint,
    lemma: rawLemma,
    surface
  });
  const language = languageFromStrongs(strongs, languageHint);

  // Prefer Hebrew surface as the human-facing lemma when OSHB only gave a number/code.
  const lemma = language === "hebrew" && surface && (/^[\d/ a]+$/u.test(rawLemma) || !rawLemma)
    ? surface
    : (rawLemma || surface);

  const reference = String(body.reference || "").trim() || "Titus 1:1";
  const clause = String(body.clause || "").trim();
  const ble = String(body.ble || body.rendering || "").trim();
  const bookId = String(body.book || "").trim().toLowerCase();
  if (!/^[a-z0-9][a-z0-9-]*$/.test(bookId)) {
    throw new Error("book id is required for a book-owned investigation");
  }
  const bookInfo = findBook(bookId);
  if (!bookInfo) {
    throw new Error(`unknown Translator book: ${bookId}`);
  }
  const book = String(body.bookLabel || "").trim() || bookInfo.label;
  const investigationsDir = join(rootDir, "investigations");
  const bookInvestigationsDir = join(investigationsDir, bookInfo.id);

  const existing = await findInvestigationByLemma(bookInvestigationsDir, { lemma, strongs, language });
  if (existing && body.force !== true) {
    return {
      created: false,
      existing: true,
      id: existing.id,
      lemma: existing.lemma || lemma,
      strongs: existing.strongs || strongs,
      language,
      status: existing.status || "Draft",
      book: bookInfo.id
    };
  }

  const id = await allocateNextInvestigationId(bookInvestigationsDir, bookInfo.number);
  const investigationDir = join(bookInvestigationsDir, id);
  const files = buildScaffold({
    id,
    lemma,
    strongs,
    reference,
    clause,
    surface,
    ble,
    book,
    language
  });

  await mkdir(join(investigationDir, "evidence"), { recursive: true });
  for (const [relativePath, content] of Object.entries(files)) {
    const target = join(investigationDir, relativePath);
    await writeFile(target, content.endsWith("\n") ? content : `${content}\n`, "utf8");
  }

  return {
    created: true,
    existing: false,
    id,
    lemma,
    strongs,
    language,
    status: "Draft",
    reference,
    book: bookInfo.id
  };
}
