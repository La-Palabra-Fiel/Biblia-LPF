import { readFile } from "node:fs/promises";
import { join } from "node:path";

const DEFAULT_OPENAI_MODEL = process.env.CGV_TRANSLATOR_OPENAI_MODEL || "gpt-4.1-mini";
const DEFAULT_ANTHROPIC_MODEL = process.env.CGV_TRANSLATOR_ANTHROPIC_MODEL || "claude-sonnet-4-5";
const DEFAULT_OLLAMA_MODEL = process.env.CGV_TRANSLATOR_OLLAMA_MODEL || "qwen2.5:7b";
const DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434";
const DEFAULT_LMSTUDIO_BASE_URL = "http://127.0.0.1:1234/v1";

let translatorRootDir = "";

export async function loadTranslatorEnv(rootDir) {
  translatorRootDir = rootDir;
  const envPath = join(rootDir, ".env");
  const content = await readFile(envPath, "utf8").catch(() => "");
  if (!content) return;

  for (const rawLine of content.replace(/\r\n/g, "\n").split("\n")) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const match = line.match(/^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$/);
    if (!match) continue;
    const [, key, rawValue] = match;
    if (process.env[key] != null && process.env[key] !== "") continue;
    let value = rawValue.trim();
    if (
      (value.startsWith("\"") && value.endsWith("\""))
      || (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    process.env[key] = value;
  }
}

export function getTranslatorRootDir() {
  return translatorRootDir;
}

function resolveOllamaBaseUrl() {
  const raw = process.env.CGV_TRANSLATOR_OLLAMA_BASE_URL
    || process.env.OLLAMA_HOST
    || DEFAULT_OLLAMA_BASE_URL;
  return String(raw).replace(/\/$/, "");
}

function resolveLmStudioBaseUrl() {
  const raw = process.env.CGV_TRANSLATOR_LMSTUDIO_BASE_URL || DEFAULT_LMSTUDIO_BASE_URL;
  const normalized = String(raw).replace(/\/+$/u, "");
  return normalized.endsWith("/v1") ? normalized : `${normalized}/v1`;
}

function getAiConfig() {
  const forced = String(process.env.CGV_TRANSLATOR_PROVIDER || "").trim().toLowerCase();
  const anthropicKey = process.env.ANTHROPIC_API_KEY || process.env.CGV_ANTHROPIC_API_KEY || "";
  const openaiKey = process.env.OPENAI_API_KEY || process.env.CGV_OPENAI_API_KEY || "";
  const ollamaBaseUrl = resolveOllamaBaseUrl();
  const ollamaModel = process.env.CGV_TRANSLATOR_OLLAMA_MODEL || DEFAULT_OLLAMA_MODEL;
  const lmStudioBaseUrl = resolveLmStudioBaseUrl();
  const lmStudioModel = String(process.env.CGV_TRANSLATOR_LMSTUDIO_MODEL || "").trim();

  if (forced === "ollama") {
    return { provider: "ollama", baseUrl: ollamaBaseUrl, model: ollamaModel };
  }
  if (forced === "lmstudio" || forced === "lm-studio") {
    return { provider: "lmstudio", baseUrl: lmStudioBaseUrl, model: lmStudioModel };
  }
  if (forced === "anthropic") {
    if (!anthropicKey) return null;
    return {
      provider: "anthropic",
      apiKey: anthropicKey,
      model: process.env.CGV_TRANSLATOR_ANTHROPIC_MODEL || DEFAULT_ANTHROPIC_MODEL
    };
  }
  if (forced === "openai") {
    if (!openaiKey) return null;
    return {
      provider: "openai",
      apiKey: openaiKey,
      model: process.env.CGV_TRANSLATOR_OPENAI_MODEL || DEFAULT_OPENAI_MODEL
    };
  }

  if (!anthropicKey && !openaiKey) {
    return { provider: "ollama", baseUrl: ollamaBaseUrl, model: ollamaModel };
  }

  if (anthropicKey) {
    return {
      provider: "anthropic",
      apiKey: anthropicKey,
      model: process.env.CGV_TRANSLATOR_ANTHROPIC_MODEL || DEFAULT_ANTHROPIC_MODEL
    };
  }

  return {
    provider: "openai",
    apiKey: openaiKey,
    model: process.env.CGV_TRANSLATOR_OPENAI_MODEL || DEFAULT_OPENAI_MODEL
  };
}

async function callOpenAi({ apiKey, model, prompt, system, json }) {
  const response = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      model,
      temperature: 0.2,
      ...(json ? { response_format: { type: "json_object" } } : {}),
      messages: [
        { role: "system", content: system },
        { role: "user", content: prompt }
      ]
    })
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body?.error?.message || `OpenAI request failed (${response.status})`);
  }

  const text = body?.choices?.[0]?.message?.content;
  if (!text || !String(text).trim()) {
    throw new Error("OpenAI returned an empty response.");
  }
  return String(text).trim();
}

async function callAnthropic({ apiKey, model, prompt, system }) {
  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      model,
      max_tokens: 1200,
      temperature: 0.2,
      system,
      messages: [{ role: "user", content: prompt }]
    })
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body?.error?.message || `Anthropic request failed (${response.status})`);
  }

  const text = (body?.content || [])
    .filter(part => part?.type === "text")
    .map(part => part.text)
    .join("")
    .trim();
  if (!text) {
    throw new Error("Anthropic returned an empty response.");
  }
  return text;
}

async function callOllama({ baseUrl, model, prompt, system, json }) {
  let response;
  try {
    response = await fetch(`${baseUrl}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model,
        stream: false,
        ...(json ? { format: "json" } : {}),
        options: { temperature: 0.2 },
        messages: [
          { role: "system", content: system },
          { role: "user", content: prompt }
        ]
      })
    });
  } catch (error) {
    const wrapped = new Error(
      `Ollama is not reachable at ${baseUrl}. Install from https://ollama.com, then run: ollama pull ${model}`
    );
    wrapped.code = "OLLAMA_UNREACHABLE";
    wrapped.cause = error;
    throw wrapped;
  }

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = body?.error || `Ollama request failed (${response.status})`;
    const error = new Error(String(detail));
    if (/not found|pull/i.test(String(detail))) {
      error.code = "OLLAMA_MODEL_MISSING";
      error.message = `${detail}. Run: ollama pull ${model}`;
    }
    throw error;
  }

  const text = body?.message?.content;
  if (!text || !String(text).trim()) {
    throw new Error("Ollama returned an empty response.");
  }
  return String(text).trim();
}

async function listLmStudioModels(baseUrl) {
  let response;
  try {
    response = await fetch(`${baseUrl}/models`, {
      method: "GET",
      signal: AbortSignal.timeout(1800)
    });
  } catch (error) {
    const wrapped = new Error(
      `LM Studio is not reachable at ${baseUrl}. Start the Local Server in LM Studio's Developer tab.`
    );
    wrapped.code = "LMSTUDIO_UNREACHABLE";
    wrapped.cause = error;
    throw wrapped;
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(body?.error?.message || `LM Studio model list failed (${response.status})`);
    error.code = "LMSTUDIO_UNREACHABLE";
    throw error;
  }
  return (Array.isArray(body?.data) ? body.data : [])
    .map(item => String(item?.id || "").trim())
    .filter(Boolean);
}

async function callLmStudio({ baseUrl, model, prompt, system, json }) {
  const availableModels = await listLmStudioModels(baseUrl);
  const selectedModel = model || availableModels[0] || "";
  if (!selectedModel) {
    const error = new Error("LM Studio is running, but it exposes no model. Load a chat model first.");
    error.code = "LMSTUDIO_MODEL_MISSING";
    throw error;
  }

  let response;
  try {
    response = await fetch(`${baseUrl}/chat/completions`, {
      method: "POST",
      headers: {
        Authorization: "Bearer lm-studio",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        model: selectedModel,
        temperature: 0.2,
        stream: false,
        ...(json ? { response_format: { type: "json_object" } } : {}),
        messages: [
          { role: "system", content: system },
          { role: "user", content: prompt }
        ]
      })
    });
  } catch (error) {
    const wrapped = new Error(
      `LM Studio is not reachable at ${baseUrl}. Start the Local Server in LM Studio's Developer tab.`
    );
    wrapped.code = "LMSTUDIO_UNREACHABLE";
    wrapped.cause = error;
    throw wrapped;
  }

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(body?.error?.message || `LM Studio request failed (${response.status})`);
    if (/model|load|not found/iu.test(error.message)) error.code = "LMSTUDIO_MODEL_MISSING";
    throw error;
  }
  const text = body?.choices?.[0]?.message?.content;
  if (!text || !String(text).trim()) {
    throw new Error("LM Studio returned an empty response.");
  }
  return String(text).trim();
}

async function listOllamaModels(baseUrl) {
  try {
    const response = await fetch(`${baseUrl}/api/tags`, {
      method: "GET",
      signal: AbortSignal.timeout(1500)
    });
    if (!response.ok) return null;
    const body = await response.json().catch(() => ({}));
    return (Array.isArray(body?.models) ? body.models : [])
      .flatMap(item => [item?.name, item?.model])
      .map(item => String(item || "").trim())
      .filter(Boolean);
  } catch {
    return null;
  }
}

export async function describeAiAvailability() {
  const config = getAiConfig();
  if (!config) {
    return {
      available: false,
      message:
        "Set CGV_TRANSLATOR_PROVIDER=lmstudio or ollama, or add ANTHROPIC_API_KEY / OPENAI_API_KEY in cgv-translator/.env"
    };
  }

  if (config.provider === "ollama") {
    const models = await listOllamaModels(config.baseUrl);
    if (models === null) {
      return {
        available: false,
        provider: "ollama",
        model: config.model,
        message:
          `Ollama not running at ${config.baseUrl}. Install from https://ollama.com, then: ollama pull ${config.model}`
      };
    }
    if (!models.includes(config.model)) {
      return {
        available: false,
        provider: "ollama",
        model: config.model,
        baseUrl: config.baseUrl,
        message: `Ollama is running, but ${config.model} is not installed. Run: ollama pull ${config.model}`
      };
    }
  }

  if (config.provider === "lmstudio") {
    try {
      const models = await listLmStudioModels(config.baseUrl);
      const selectedModel = config.model || models[0] || "";
      if (!selectedModel) {
        return {
          available: false,
          provider: "lmstudio",
          baseUrl: config.baseUrl,
          message: "LM Studio is running, but no model is exposed. Load a chat model first."
        };
      }
      return {
        available: true,
        provider: "lmstudio",
        model: selectedModel,
        baseUrl: config.baseUrl
      };
    } catch (error) {
      return {
        available: false,
        provider: "lmstudio",
        baseUrl: config.baseUrl,
        message: error.message || "LM Studio is unavailable."
      };
    }
  }

  return {
    available: true,
    provider: config.provider,
    model: config.model,
    ...(["ollama", "lmstudio"].includes(config.provider) ? { baseUrl: config.baseUrl } : {})
  };
}

export async function runChatCompletion({
  prompt,
  system = "You assist LPF. Follow the user instructions exactly.",
  json = false
} = {}) {
  const config = getAiConfig();
  if (!config) {
    const error = new Error(
      "No AI provider configured. Use LM Studio or Ollama locally, or set ANTHROPIC_API_KEY / OPENAI_API_KEY in .env"
    );
    error.code = "AI_NOT_CONFIGURED";
    throw error;
  }

  if (config.provider === "ollama") {
    return callOllama({
      baseUrl: config.baseUrl,
      model: config.model,
      prompt,
      system,
      json
    });
  }
  if (config.provider === "lmstudio") {
    return callLmStudio({
      baseUrl: config.baseUrl,
      model: config.model,
      prompt,
      system,
      json
    });
  }
  if (config.provider === "anthropic") {
    return callAnthropic({
      apiKey: config.apiKey,
      model: config.model,
      prompt,
      system
    });
  }
  return callOpenAi({
    apiKey: config.apiKey,
    model: config.model,
    prompt,
    system,
    json
  });
}
