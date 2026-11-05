const DEFAULT_BASE_URL = "http://127.0.0.1:11434";

export function ollamaBaseUrl() {
  return String(process.env.LBF_OLLAMA_BASE_URL || process.env.OLLAMA_HOST || DEFAULT_BASE_URL).replace(/\/+$/u, "");
}

export async function listOllamaModels() {
  const baseUrl = ollamaBaseUrl();
  let response;
  try {
    response = await fetch(`${baseUrl}/api/tags`, { signal: AbortSignal.timeout(2500) });
  } catch (error) {
    const wrapped = new Error(`Ollama is not reachable at ${baseUrl}. Start Ollama, then refresh models.`);
    wrapped.code = "OLLAMA_UNREACHABLE";
    wrapped.cause = error;
    throw wrapped;
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(body?.error || `Ollama returned ${response.status}.`);
    error.code = "OLLAMA_UNREACHABLE";
    throw error;
  }
  const seen = new Set();
  return (Array.isArray(body.models) ? body.models : []).flatMap(item => {
    const name = String(item?.model || item?.name || "").trim();
    if (!name || seen.has(name)) return [];
    seen.add(name);
    return [{
      name,
      size: Number(item?.size || 0),
      parameterSize: String(item?.details?.parameter_size || ""),
      quantization: String(item?.details?.quantization_level || "")
    }];
  });
}

function translationSchema(references) {
  return {
    type: "object",
    properties: {
      translations: {
        type: "array",
        minItems: references.length,
        maxItems: references.length,
        items: {
          type: "object",
          properties: {
            reference: { type: "string", enum: references },
            spanish: { type: "string" }
          },
          required: ["reference", "spanish"]
        }
      }
    },
    required: ["translations"]
  };
}

function promptForChunk({ book, verses, previousSpanish }) {
  const payload = verses.map(verse => ({
    reference: `${verse.chapter}:${verse.verse}`,
    source: verse.sourceText,
    morphology: verse.morphology
  }));
  return `Translate the supplied source-language verses into faithful, contemporary Spanish for LPF.

TRANSLATOR'S OATH
The translator is not the author. Do not improve, soften, strengthen, harmonize, explain, modernize the theology, or add what the source leaves unsaid. Preserve repetition, questions, tension, simplicity, force, ambiguity, and silence. Say neither more nor less than the source.

TEXTUAL BASIS
${book.testament === "nt"
    ? "New Testament: Scrivener 1894 Textus Receptus. The accented Greek is controlling; Robinson morphology is helper evidence."
    : "Old Testament: OSHB / WLC Hebrew and Aramaic. Working labels are Protestant/KJV coordinates; morphology is helper evidence."}

RULES
- Translate directly from the supplied Hebrew, Aramaic, or Greek, not from memory or another Spanish Bible.
- Produce natural contemporary Spanish while preserving source grammar, discourse, names, and theological terms.
- Translate every requested verse exactly once. Never merge, omit, split, renumber, or add verses.
- Return only the JSON object required by the schema. Do not include Markdown or commentary.
- Each spanish value must contain only that verse's Spanish text, without a verse number.
- Existing nearby LBF text is context only. Do not rewrite it.

PREVIOUS LBF CONTEXT
${previousSpanish.length ? previousSpanish.map(item => `${item.reference} ${item.spanish}`).join("\n") : "(none)"}

SOURCE VERSES
${JSON.stringify(payload, null, 2)}`;
}

export async function translateChunk({ model, book, verses, previousSpanish = [] }) {
  const installed = await listOllamaModels();
  if (!installed.some(item => item.name === model)) {
    const error = new Error(`The selected Ollama model is not installed: ${model}`);
    error.code = "OLLAMA_MODEL_MISSING";
    throw error;
  }
  const references = verses.map(verse => `${verse.chapter}:${verse.verse}`);
  const schema = translationSchema(references);
  let response;
  try {
    response = await fetch(`${ollamaBaseUrl()}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model,
        stream: false,
        format: schema,
        keep_alive: "10m",
        options: { temperature: 0, num_ctx: 16384 },
        messages: [
          {
            role: "system",
            content: "You are a suggestion-only source-language Bible translator. A human must review all output. Return valid JSON only."
          },
          { role: "user", content: promptForChunk({ book, verses, previousSpanish }) }
        ]
      })
    });
  } catch (error) {
    const wrapped = new Error(`Ollama stopped responding at ${ollamaBaseUrl()}.`);
    wrapped.code = "OLLAMA_UNREACHABLE";
    wrapped.cause = error;
    throw wrapped;
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(body?.error || `Ollama request failed (${response.status}).`);
    error.code = /model|not found|pull/iu.test(error.message) ? "OLLAMA_MODEL_MISSING" : "OLLAMA_REQUEST_FAILED";
    throw error;
  }
  let parsed;
  try {
    parsed = JSON.parse(String(body?.message?.content || ""));
  } catch {
    const error = new Error("The model returned invalid JSON. Try a stronger model or a smaller chunk size.");
    error.code = "INVALID_MODEL_OUTPUT";
    throw error;
  }
  return validateTranslations(parsed?.translations, references);
}

export function validateTranslations(items, references) {
  if (!Array.isArray(items)) throw new Error("The model response has no translations array.");
  const requested = new Set(references);
  const accepted = new Map();
  for (const item of items) {
    const reference = String(item?.reference || "").trim();
    const spanish = String(item?.spanish || "")
      .replace(/\s*\n+\s*/gu, " ")
      .replace(/\s+/gu, " ")
      .trim();
    if (!requested.has(reference) || accepted.has(reference)) continue;
    if (!spanish || /^#{1,6}\s/u.test(spanish) || /^(?:cap[ií]tulo|vers[ií]culo)\b/iu.test(spanish)) continue;
    if (/^[\d\s:.-]+$/u.test(spanish)) continue;
    accepted.set(reference, spanish);
  }
  const missing = references.filter(reference => !accepted.has(reference));
  if (missing.length) {
    const error = new Error(`The model omitted or malformed: ${missing.join(", ")}`);
    error.code = "INCOMPLETE_MODEL_OUTPUT";
    throw error;
  }
  return accepted;
}
