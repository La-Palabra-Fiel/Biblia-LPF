/**
 * Export approved LBF phrases to Biblia-LBF verse-structured Markdown.
 */
import { mkdir, writeFile } from "node:fs/promises";
import { join } from "node:path";

function verseKey(reference) {
  const m = String(reference || "").match(/(\d+):(\d+)\s*$/u);
  if (!m) return { chapter: 0, verse: 0 };
  return { chapter: Number(m[1]), verse: Number(m[2]) };
}

function isApproved(phrase) {
  const status = phrase?.approval?.status || phrase?.suggestionSource || "";
  return status === "approved" || status === "lbf-approved";
}

/**
 * Build verse-structured markdown from phrase records.
 * Only approved phrases are included in the running LBF text (drafts noted in comments).
 */
export function buildLbfMarkdown({ bookLabel = "Titus", phrases = [], includeDrafts = false } = {}) {
  const byVerse = new Map();
  for (const phrase of phrases) {
    if (!includeDrafts && !isApproved(phrase)) continue;
    const spanish = String(phrase.spanish || "").trim();
    if (!spanish) continue;
    const { chapter, verse } = verseKey(phrase.reference);
    const key = `${chapter}:${verse}`;
    if (!byVerse.has(key)) {
      byVerse.set(key, {
        chapter,
        verse,
        reference: phrase.reference,
        parts: []
      });
    }
    byVerse.get(key).parts.push({
      phraseIndex: Number(phrase.phraseIndex) || 0,
      spanish,
      approved: isApproved(phrase)
    });
  }

  const verses = [...byVerse.values()].sort((a, b) => a.chapter - b.chapter || a.verse - b.verse);
  const lines = [
    `# ${bookLabel}`,
    "",
    "> LPF — borrador de trabajo. Solo texto aprobado entra en el cuerpo.",
    ""
  ];

  let currentChapter = null;
  for (const v of verses) {
    if (v.chapter !== currentChapter) {
      currentChapter = v.chapter;
      lines.push(`## Capítulo ${currentChapter}`, "");
    }
    const text = v.parts
      .sort((a, b) => a.phraseIndex - b.phraseIndex)
      .map(p => p.spanish)
      .join(" ")
      .replace(/\s+/g, " ")
      .trim();
    lines.push(`### ${v.chapter}:${v.verse}`, "", text, "");
  }
  return `${lines.join("\n").trim()}\n`;
}

export async function exportBookToBibliaLbf({
  rootDir,
  bookId = "titus",
  bookLabel = "Tito",
  testament = "nt",
  phrases = [],
  includeDrafts = false
} = {}) {
  const outDir = join(rootDir, "..", "Biblia-LBF", "translation", testament);
  await mkdir(outDir, { recursive: true });
  const markdown = buildLbfMarkdown({ bookLabel, phrases, includeDrafts });
  const outPath = join(outDir, `${bookId}.md`);
  await writeFile(outPath, markdown, "utf8");
  return { outPath, verseCount: (markdown.match(/^### /gmu) || []).length };
}
