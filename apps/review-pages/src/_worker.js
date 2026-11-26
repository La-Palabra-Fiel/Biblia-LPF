const JSON_HEADERS = {
  "Content-Type": "application/json; charset=utf-8",
  "Cache-Control": "no-store",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer",
};

function json(value, status = 200) {
  return new Response(JSON.stringify(value), { status, headers: JSON_HEADERS });
}

export function normalizeName(value) {
  return String(value ?? "").normalize("NFC").trim().replace(/\s+/g, " ").toLocaleLowerCase("es");
}

export async function sha256Hex(value) {
  const bytes = new TextEncoder().encode(String(value));
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function payload(request) {
  const length = Number(request.headers.get("content-length") || 0);
  if (length > 8192) throw new Error("La solicitud es demasiado grande.");
  try {
    return await request.json();
  } catch {
    throw new Error("La solicitud no es válida.");
  }
}

function validBook(value) {
  const slug = String(value ?? "");
  if (!/^[a-z0-9]+$/.test(slug)) throw new Error("El libro no es válido.");
  return slug;
}

async function authorize(env, book, accessKey) {
  const submitted = String(accessKey ?? "");
  if (submitted.length < 24 || submitted.length > 128) throw new Error("Este enlace privado no es válido.");
  const tokenHash = await sha256Hex(submitted);
  const row = await env.DB.prepare(
    "SELECT reviewer, reviewer_key FROM review_links WHERE book = ? AND token_hash = ? AND revoked_on IS NULL"
  ).bind(book, tokenHash).first();
  if (!row) throw new Error("Este enlace privado no es válido.");
  return row;
}

async function loadBook(env, request, book) {
  const url = new URL(`/books/${book}.json`, request.url);
  const response = await env.ASSETS.fetch(new Request(url, { method: "GET" }));
  if (!response.ok) throw new Error("Este libro no está disponible para revisión.");
  return response.json();
}

async function currentSignatures(env, book, fingerprint) {
  const result = await env.DB.prepare(
    "SELECT signed_name AS name, signed_on AS signedOn FROM signatures WHERE book = ? AND translation_sha256 = ? ORDER BY signed_on"
  ).bind(book, fingerprint).all();
  return result.results || [];
}

async function bookView(env, request, body) {
  const book = validBook(body.book);
  const reviewer = await authorize(env, book, body.accessKey);
  const data = await loadBook(env, request, book);
  return {
    ...data,
    reviewer: reviewer.reviewer,
    signatures: await currentSignatures(env, book, data.translationSha256),
  };
}

async function sign(env, request, body) {
  const book = validBook(body.book);
  const reviewer = await authorize(env, book, body.accessKey);
  const data = await loadBook(env, request, book);
  if (!new Set(["ready", "done"]).has(data.status)) {
    throw new Error(`${data.label} todavía no está listo para la aprobación del libro completo.`);
  }
  if (body.confirmed !== true) throw new Error("Confirma que leíste el libro completo y apruebas esta traducción.");
  const signedName = String(body.signedName ?? "").normalize("NFC").trim().replace(/\s+/g, " ");
  if (!signedName || normalizeName(signedName) !== reviewer.reviewer_key) {
    throw new Error("El nombre escrito no coincide con la persona asignada a este enlace privado.");
  }
  if (body.translationSha256 !== data.translationSha256) {
    throw new Error("La traducción cambió. Vuelve a cargar el libro antes de firmar.");
  }
  try {
    await env.DB.prepare(
      "INSERT INTO signatures (book, reviewer, reviewer_key, signed_name, signed_on, translation_sha256, statement) VALUES (?, ?, ?, ?, ?, ?, ?)"
    ).bind(
      book,
      reviewer.reviewer,
      reviewer.reviewer_key,
      signedName,
      new Date().toISOString(),
      data.translationSha256,
      "La persona nombrada confirmó que leyó el libro completo y aprobó esta traducción española exacta."
    ).run();
  } catch (error) {
    if (String(error).includes("UNIQUE")) throw new Error(`${reviewer.reviewer} ya firmó esta versión de ${data.label}.`);
    throw error;
  }
  return bookView(env, request, body);
}

export async function handleRequest(request, env) {
  const url = new URL(request.url);
  if (request.method === "POST" && url.pathname === "/api/revision-libros/libro") {
    return json(await bookView(env, request, await payload(request)));
  }
  if (request.method === "POST" && url.pathname === "/api/revision-libros/firmar") {
    return json(await sign(env, request, await payload(request)));
  }
  return env.ASSETS.fetch(request);
}

export default {
  async fetch(request, env) {
    try {
      return await handleRequest(request, env);
    } catch (error) {
      console.error(JSON.stringify({ event: "peer_review_error", path: new URL(request.url).pathname, error: String(error) }));
      return json({ error: error instanceof Error ? error.message : "No se pudo completar la acción." }, 400);
    }
  },
};

