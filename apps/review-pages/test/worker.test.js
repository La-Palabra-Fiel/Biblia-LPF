import assert from "node:assert/strict";
import test from "node:test";
import { handleRequest, normalizeName, sha256Hex } from "../src/_worker.js";

test("normaliza nombres españoles sin cambiar acentos", () => {
  assert.equal(normalizeName("  Ana   Pérez  "), "ana pérez");
});

test("genera una huella SHA-256 estable", async () => {
  assert.equal(
    await sha256Hex("enlace privado"),
    "6f4036c52d56e9f19ae1d7d67daf04936c3d52c8ff926fc7ac2e3cbad6694207",
  );
});

class FakeDatabase {
  constructor(link) {
    this.link = link;
    this.signatures = [];
  }

  prepare(sql) {
    const progressRows = () => {
      const groups = new Map();
      this.signatures.forEach((row) => {
        const key = `${row.book}:${row.translation_sha256}`;
        const known = groups.get(key) || {
          book: row.book, translation_sha256: row.translation_sha256,
          completed: 0, updated_on: row.signed_on,
        };
        known.completed += 1;
        if (row.signed_on > known.updated_on) known.updated_on = row.signed_on;
        groups.set(key, known);
      });
      return { results: [...groups.values()] };
    };
    return {
      all: async () => {
        if (!sql.startsWith("SELECT book, translation_sha256")) throw new Error(`Consulta inesperada: ${sql}`);
        return progressRows();
      },
      bind: (...values) => ({
        first: async () => {
          if (!sql.startsWith("SELECT reviewer,")) throw new Error(`Consulta inesperada: ${sql}`);
          return values[0] === this.link.book && values[1] === this.link.tokenHash ? this.link : null;
        },
        all: async () => {
          if (!sql.startsWith("SELECT signed_name")) throw new Error(`Consulta inesperada: ${sql}`);
          return {
            results: this.signatures
              .filter((row) => row.book === values[0] && row.translation_sha256 === values[1])
              .map((row) => ({ name: row.signed_name, signedOn: row.signed_on })),
          };
        },
        run: async () => {
          if (!sql.startsWith("INSERT INTO signatures")) throw new Error(`Consulta inesperada: ${sql}`);
          this.signatures.push({
            book: values[0], reviewer: values[1], reviewer_key: values[2], signed_name: values[3],
            signed_on: values[4], translation_sha256: values[5], statement: values[6],
          });
          return { success: true };
        },
      }),
    };
  }
}

async function environment() {
  const token = "token-privado-con-suficiente-entropia";
  const book = {
    book: "romanos",
    label: "Romanos",
    status: "ready",
    translationSha256: "a".repeat(64),
    chapters: [{ chapter: 1, verses: [{ verse: 1, text: "Pablo…" }] }],
  };
  const DB = new FakeDatabase({
    book: "romanos",
    reviewer: "Ana Pérez",
    reviewer_key: "ana pérez",
    tokenHash: await sha256Hex(token),
  });
  const ASSETS = {
    fetch: async (request) => new URL(request.url).pathname === "/books/romanos.json"
      ? Response.json(book)
      : new Response("No encontrado", { status: 404 }),
  };
  return { token, book, env: { DB, ASSETS } };
}

test("abre el libro solamente con su enlace privado", async () => {
  const { token, env } = await environment();
  const response = await handleRequest(new Request("https://revision.example/api/revision-libros/libro", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ book: "romanos", accessKey: token }),
  }), env);
  assert.equal(response.status, 200);
  assert.equal((await response.json()).reviewer, "Ana Pérez");
});

test("la firma exige que la persona escriba su propio nombre", async () => {
  const { token, book, env } = await environment();
  const request = (signedName) => new Request("https://revision.example/api/revision-libros/firmar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      book: "romanos", accessKey: token, signedName, confirmed: true,
      translationSha256: book.translationSha256,
    }),
  });
  await assert.rejects(() => handleRequest(request("Otra Persona"), env), /no coincide/);
  const response = await handleRequest(request("Ana Pérez"), env);
  assert.equal(response.status, 200);
  assert.equal(env.DB.signatures.length, 1);
  assert.equal(env.DB.signatures[0].signed_name, "Ana Pérez");
});

test("el progreso público expone conteos anónimos ligados a la traducción", async () => {
  const { book, env } = await environment();
  env.DB.signatures.push({
    book: "romanos", reviewer: "Ana Pérez", reviewer_key: "ana pérez",
    signed_name: "Ana Pérez", signed_on: "2026-11-26T03:16:16.058Z",
    translation_sha256: book.translationSha256, statement: "confirmado",
  });
  const response = await handleRequest(
    new Request("https://revision.example/api/revision-libros/progreso"), env,
  );
  const value = await response.json();
  assert.equal(response.headers.get("Access-Control-Allow-Origin"), "*");
  assert.equal(value.books.romanos[book.translationSha256].completed, 1);
  assert.equal(JSON.stringify(value).includes("Ana Pérez"), false);
});

