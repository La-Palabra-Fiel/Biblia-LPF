import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import { dirname } from "node:path";

const VERSE_HEADING = /^###\s+(\d+):(\d+)\s*$/gmu;

export async function readTranslationDocument(path) {
  const text = await readFile(path, "utf8").catch(() => "");
  const verses = new Map();
  const matches = [...text.matchAll(VERSE_HEADING)];
  for (let index = 0; index < matches.length; index += 1) {
    const match = matches[index];
    const bodyStart = match.index + match[0].length;
    const bodyEnd = matches[index + 1]?.index ?? text.length;
    const body = text.slice(bodyStart, bodyEnd)
      .split("\n")
      .filter(line => !/^##\s+Capítulo\s+\d+\s*$/u.test(line.trim()))
      .join("\n")
      .trim();
    verses.set(`${Number(match[1])}:${Number(match[2])}`, body);
  }
  return { text, verses };
}

export function renderTranslationDocument(book, verses) {
  const rows = [...verses.entries()]
    .map(([reference, text]) => {
      const [chapter, verse] = reference.split(":").map(Number);
      return { chapter, verse, text: String(text || "").trim() };
    })
    .filter(row => Number.isInteger(row.chapter) && Number.isInteger(row.verse) && row.text)
    .sort((a, b) => a.chapter - b.chapter || a.verse - b.verse);

  const lines = [
    `# ${book.title}`,
    "",
    `> LPF — ${book.title}. Borrador de primera pasada generado por IA con Ollama; requiere revisión humana completa.`,
    `> Fuente: ${book.textualBasis}.`,
    ""
  ];
  let chapter = null;
  for (const row of rows) {
    if (row.chapter !== chapter) {
      chapter = row.chapter;
      lines.push(`## Capítulo ${chapter}`, "");
    }
    lines.push(`### ${row.chapter}:${row.verse}`, "", row.text, "");
  }
  return `${lines.join("\n").trim()}\n`;
}

export async function writeTranslationDocument(path, book, verses) {
  await mkdir(dirname(path), { recursive: true });
  const temporaryPath = `${path}.ai-first-pass.tmp`;
  await writeFile(temporaryPath, renderTranslationDocument(book, verses), "utf8");
  await rename(temporaryPath, path);
}
