import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";
import { BatchRunner } from "./src/batch-runner.js";
import { findBook } from "./src/catalog.js";
import { listOllamaModels, ollamaBaseUrl } from "./src/ollama.js";
import { loadBookSource } from "./src/source-loader.js";
import { readTranslationDocument } from "./src/translation-document.js";

const appRoot = fileURLToPath(new URL(".", import.meta.url));
const repoRoot = join(appRoot, "..", "..");
const publicRoot = join(appRoot, "public");
const port = Number(process.env.PORT || 1430);
const runner = new BatchRunner(repoRoot);

const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".svg": "image/svg+xml"
};

function send(response, statusCode, body, contentType = "text/plain; charset=utf-8") {
  response.writeHead(statusCode, {
    "Content-Type": contentType,
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff"
  });
  response.end(body);
}

function sendJson(response, statusCode, value) {
  send(response, statusCode, JSON.stringify(value), "application/json; charset=utf-8");
}

async function readJsonBody(request) {
  let body = "";
  for await (const chunk of request) {
    body += chunk;
    if (body.length > 1_000_000) throw Object.assign(new Error("Request is too large."), { code: "REQUEST_TOO_LARGE" });
  }
  if (!body.trim()) return {};
  try {
    return JSON.parse(body);
  } catch {
    throw Object.assign(new Error("Request body must be valid JSON."), { code: "INVALID_JSON" });
  }
}

async function handleApi(request, response, url) {
  if (request.method === "GET" && url.pathname === "/api/models") {
    try {
      sendJson(response, 200, { available: true, baseUrl: ollamaBaseUrl(), models: await listOllamaModels() });
    } catch (error) {
      sendJson(response, 503, { available: false, baseUrl: ollamaBaseUrl(), models: [], error: error.message, code: error.code });
    }
    return;
  }

  if (request.method === "GET" && url.pathname === "/api/books") {
    sendJson(response, 200, { books: await runner.scanBooks() });
    return;
  }

  if (request.method === "GET" && url.pathname === "/api/book") {
    const book = findBook(url.searchParams.get("book"));
    if (!book) return sendJson(response, 404, { error: "Unknown book." });
    const [source, document] = await Promise.all([
      loadBookSource(repoRoot, book),
      readTranslationDocument(join(repoRoot, "translation", book.testament, `${book.slug}.md`))
    ]);
    const missing = source
      .filter(verse => !document.verses.has(`${verse.chapter}:${verse.verse}`))
      .sort((left, right) => Number(right.sourceUnavailable) - Number(left.sourceUnavailable));
    sendJson(response, 200, {
      book,
      missingVerses: missing.length,
      preview: missing.slice(0, 4).map(verse => ({
        reference: `${book.title} ${verse.chapter}:${verse.verse}`,
        sourceText: verse.sourceText,
        morphology: verse.morphology,
        sourceUnavailable: verse.sourceUnavailable,
        sourceNote: verse.sourceNote
      }))
    });
    return;
  }

  if (request.method === "GET" && url.pathname === "/api/job") {
    sendJson(response, 200, runner.status());
    return;
  }

  if (request.method === "POST" && url.pathname === "/api/job/start") {
    sendJson(response, 202, await runner.start(await readJsonBody(request)));
    return;
  }

  if (request.method === "POST" && url.pathname === "/api/job/stop") {
    sendJson(response, 200, runner.requestStop());
    return;
  }

  sendJson(response, 404, { error: "Not found." });
}

async function handleStatic(response, url) {
  const requested = url.pathname === "/" ? "index.html" : url.pathname.slice(1);
  const safePath = normalize(requested).replace(/^(\.\.(\/|\\|$))+/u, "");
  const path = join(publicRoot, safePath);
  if (!path.startsWith(publicRoot)) return send(response, 403, "Forbidden");
  try {
    const info = await stat(path);
    if (!info.isFile()) return send(response, 404, "Not found");
    send(response, 200, await readFile(path), contentTypes[extname(path)] || "application/octet-stream");
  } catch {
    send(response, 404, "Not found");
  }
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url || "/", `http://${request.headers.host || "127.0.0.1"}`);
  try {
    if (url.pathname.startsWith("/api/")) await handleApi(request, response, url);
    else await handleStatic(response, url);
  } catch (error) {
    const statusCode = ["CONFIRMATION_REQUIRED", "INVALID_JSON"].includes(error.code) ? 400
      : error.code === "JOB_RUNNING" ? 409
        : error.code === "REQUEST_TOO_LARGE" ? 413
          : 500;
    sendJson(response, statusCode, { error: error.message || "Unexpected error.", code: error.code || "INTERNAL_ERROR" });
  }
});

server.listen(port, "127.0.0.1", () => {
  console.log(`LPF AI First Pass: http://127.0.0.1:${port}/`);
  console.log(`Ollama: ${ollamaBaseUrl()}`);
});
