import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { runChatCompletion, describeAiAvailability } from "../ai/suggestPhrase.js";

async function loadTranslationRules(rootDir) {
  const rulesPath = join(rootDir, "src", "ai", "lbf-translation-rules.md");
  return readFile(rulesPath, "utf8").catch(() => "");
}

function extractJsonObject(text) {
  const raw = String(text || "").trim();
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    // continue
  }
  const fenced = raw.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fenced) {
    try {
      return JSON.parse(fenced[1].trim());
    } catch {
      // continue
    }
  }
  const start = raw.indexOf("{");
  const end = raw.lastIndexOf("}");
  if (start >= 0 && end > start) {
    try {
      return JSON.parse(raw.slice(start, end + 1));
    } catch {
      return null;
    }
  }
  return null;
}

function cleanProposal(text) {
  return String(text || "")
    .trim()
    .replace(/^["«“]|["»”]$/gu, "")
    .replace(/\s+/gu, " ")
    .trim();
}

function scrubSummary(value) {
  return String(value || "")
    .replace(/esperanza de vida eterna|mandato de Dios|nuestro Salvador/gi, "[removed later-verse import]")
    .trim();
}

function sourceLanguageLabel(analysis) {
  const source = String(analysis?.greek || "");
  const constraints = analysis?.gates?.morphology?.constraints || [];
  const strongs = constraints.map(item => String(item.strongs || "")).join(" ");
  if (/[\u0590-\u05ff]/u.test(source) || /\bH\d+/iu.test(strongs)) return "Hebrew/Aramaic";
  if (/[\u0370-\u03ff\u1f00-\u1fff]/u.test(source) || /\bG\d+/iu.test(strongs)) return "Greek";
  return "biblical source language";
}

export function buildTranslatePrompt({ analysis, rulesMarkdown, rv1909Text }) {
  const { gates, readyForSynthesis, reference, greek, mechanicalDraft } = analysis;
  const sourceLanguage = sourceLanguageLabel(analysis);
  const sourceSpecificRules = sourceLanguage === "Greek"
    ? `3. πιστεύω in PASSIVE (ἐπιστεύθην) = "was entrusted / me fue confiada", NEVER "creí/believed".
4. Possessive genitives: αὐτοῦ/ἡμῶν → su/nuestro before the noun (su palabra, nuestro Salvador), not "de él/de nosotros".
5. τοῦ σωτῆρος ἡμῶν θεοῦ ≈ "de Dios nuestro Salvador" or "de nuestro Salvador Dios", not "Salvador de nosotros, Dios".
6. ἰδίοις with καιροῖς = "tiempos propios / sus tiempos", NEVER "tiempos escogidos".
7. Soft δέ: do not force "y"; "pero tú…" is fine when addressing resumes the discourse.
8. ἰδίοις ἀνδράσιν (household) → "sus propios maridos", not "varones".`
    : `3. Treat Hebrew/Aramaic morphology and syntax as the source of sentence structure; disconnected Spanish glosses do not supply syntax.
4. Translate the spine token. Nested qere is evidence only; do not substitute it for the snapshot token or fuse both readings into one proposal.
5. Strong's numbers identify source lexemes/senses; they do not prove a particular Spanish wording or historical-version alignment.
6. Do not claim that a historical witness translates a source word unless an alignment is explicitly recorded.`;
  const morphLines = (gates.morphology?.constraints || []).map(c =>
    `- ${c.greek} | ${c.morphology} | ${c.explanation} | ${ (c.requirements || []).join("; ") }`
  ).join("\n");
  const lemmaLines = (gates.lemma?.tokens || [])
    .filter(t => t.significant)
    .map(t =>
      `- ${t.greek} (${t.lemma}${t.strongs ? ` ${t.strongs}` : ""}): ${
        t.allowedRenderings?.length
          ? `specific approved rendering ${t.allowedRenderings.join("/")} (${t.policyScope || "scoped"})`
          : t.guidanceRendering
            ? `book-default lexical guidance: ${t.guidanceRendering}; inflect/realize according to morphology and syntax`
            : t.status === "blocked"
              ? "BLOCKED — no applicable approved decision"
              : "no applicable approved decision yet"
      }`
    )
    .join("\n");

  const verseWindow = gates.generalContext?.verseWindow || [];
  const discourseLines = [
    ...(gates.generalContext?.notes || []).map(n => `- ${n}`),
    ...verseWindow.map(v =>
      `- [${v.role}] ${v.reference}: ${v.greek}${v.rv1909 ? ` ‖ RV1909: ${v.rv1909}` : ""}`
    )
  ].join("\n");

  return `${rulesMarkdown}

---

TASK
Produce one modern Spanish rendering for this ${sourceLanguage} phrase.
It must be faithful to the source grammar and genuinely grammatical, idiomatic Spanish.

Reference: ${reference}
${sourceLanguage}: ${greek}

HARD GRAMMAR CONSTRAINTS (do not violate):
${morphLines || "(none)"}

LEMMA POLICY:
${lemmaLines || "(none)"}

SYNTAX NOTES (immediate phrase):
${(gates.immediateContext?.structure?.notes || []).map(n => `- ${n}`).join("\n") || "(none)"}

GENERAL CONTEXT (verse → paragraph → book — clarify among morph-valid options only):
${discourseLines || "(none)"}
Scope: ${(gates.generalContext?.scope || []).join(" · ") || "—"}

DIAGNOSTIC GLOSS STREAM (evidence only; NEVER return this as the Spanish draft):
Template: ${mechanicalDraft?.template || "—"}
Mechanical: ${mechanicalDraft?.proposedSpanish || "—"}

RV1909 for THIS phrase (consultative style only — do not copy archaic wording; do not start from it):
${rv1909Text || "—"}
RV1909 flags: ${(gates.rv1909Review?.flags || []).map(f => f.note).join(" | ") || "none"}

Rules:
1. Translate FROM the ${sourceLanguage} source. RV1909 is consultative only.
2. Preserve number, verbal force, syntax, and dependencies recorded by the gates.
${sourceSpecificRules}
9. Prefer readings that fit the verse/paragraph discourse above when multiple morph-valid options exist.
10. Use contemporary Spanish that flows naturally (never RV1909 spelling like "á").
11. Do not add subjects, copulas, or theology absent from this phrase.
12. Articles and smooth phrasing are allowed when Spanish requires them and the source sense remains.
13. Translate ONLY this phrase span — do not pull wording from the next source phrase or later RV1909 clauses.
14. If readyForSynthesis=${readyForSynthesis} is false, set proposedSpanish to null.
15. The Mechanical line is a word-by-word diagnostic, not a sentence. Do not copy it, lightly punctuate it, or merely reorder its words.
16. Before returning, silently read proposedSpanish as a standalone Spanish sentence. If it is not grammatical and readily understandable, set proposedSpanish to null and explain why in flags.
17. Return JSON only:

{
  "gateSummaries": {
    "lemma": "one sentence",
    "morphology": "one sentence",
    "immediateContext": "one sentence",
    "generalContext": "one sentence citing verse/paragraph",
    "rv1909Review": "one sentence"
  },
  "proposedSpanish": "modern faithful Spanish phrase",
  "rationale": ["short bullets citing source-language + discourse constraints"],
  "flags": [],
  "blockedNote": null
}`;
}

function normalizeDraftComparison(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/gu, "")
    .toLocaleLowerCase("es")
    .replace(/[•·]/gu, " ")
    .replace(/[^a-zñ0-9]+/giu, " ")
    .trim()
    .replace(/\s+/gu, " ");
}

function mechanicalCopyScore(draft, mechanical) {
  const draftTokens = normalizeDraftComparison(draft).split(" ").filter(Boolean);
  const mechanicalTokens = normalizeDraftComparison(mechanical).split(" ").filter(Boolean);
  if (!draftTokens.length || !mechanicalTokens.length) return 0;

  const counts = new Map();
  for (const token of mechanicalTokens) counts.set(token, (counts.get(token) || 0) + 1);
  let shared = 0;
  for (const token of draftTokens) {
    const remaining = counts.get(token) || 0;
    if (remaining > 0) {
      shared += 1;
      counts.set(token, remaining - 1);
    }
  }
  return shared / Math.max(draftTokens.length, mechanicalTokens.length);
}

function normalizeHebrew(value) {
  return String(value || "")
    .replace(/[\u0591-\u05c7]/gu, "")
    .replace(/[^\u05d0-\u05ea]+/gu, " ")
    .trim()
    .replace(/\s+/gu, " ");
}

function inventedHebrewCitations(rationale, sourceText) {
  const sourceWords = new Set(normalizeHebrew(sourceText).split(" ").filter(Boolean));
  const cited = (Array.isArray(rationale) ? rationale : [])
    .flatMap(item => String(item || "").match(/[\u0590-\u05ff]+/gu) || [])
    .map(normalizeHebrew)
    .filter(word => word.length >= 2);
  return [...new Set(cited.filter(word => !sourceWords.has(word)))];
}

export function validateDraftAgainstGates(draft, analysis, rationale = []) {
  const flags = [];
  const text = String(draft || "");
  const morphConstraints = analysis?.gates?.morphology?.constraints || [];
  const lemmaTokens = analysis?.gates?.lemma?.tokens || [];
  const mechanical = String(analysis?.mechanicalDraft?.proposedSpanish || "");
  const normalizedText = normalizeDraftComparison(text);
  const normalizedMechanical = normalizeDraftComparison(mechanical);

  if (!normalizedText) {
    flags.push("Rejected: the model returned no usable Spanish draft.");
  }
  if (/[•·]/u.test(text)) {
    flags.push("Rejected: the proposal contains diagnostic gloss separators, not normal Spanish prose.");
  }
  if (normalizedMechanical && normalizedText === normalizedMechanical) {
    flags.push("Rejected: the proposal copies the mechanical gloss stream instead of producing grammatical Spanish.");
  } else if (
    normalizedMechanical.split(" ").length >= 6
    && mechanicalCopyScore(text, mechanical) >= 0.8
  ) {
    flags.push("Rejected: the proposal is only a light rearrangement of the mechanical gloss stream.");
  }

  const inventedCitations = inventedHebrewCitations(rationale, analysis?.greek || "");
  if (inventedCitations.length) {
    flags.push(`Rejected: the rationale cites source word(s) not present in this phrase: ${inventedCitations.join(", ")}.`);
  }

  const sourceStrongs = new Set(
    lemmaTokens.map(item => String(item.strongs || "").toUpperCase()).filter(Boolean)
  );
  const permitsLordTitle = ["H113", "H136", "H1167", "H3068", "H410", "H430"]
    .some(strongs => sourceStrongs.has(strongs));
  if (!permitsLordTitle && /\b(?:el\s+)?señor\b|\bYHWH\b|\bDios\b/iu.test(text)) {
    flags.push("Rejected: the proposal adds a divine/master title absent from the selected source tokens.");
  }

  for (const item of morphConstraints) {
    if (/ἐκλεκτ/u.test(item.lemma || "") || /ἐκλεκτ/u.test(item.greek || "")) {
      if (/\bfe elegida\b/i.test(text) || /\bfe escogida\b/i.test(text)) {
        flags.push("Rejected: ἐκλεκτῶν cannot become attributive 'fe elegida/escogida'.");
      }
      if (item.number === "plural" && (/\bel elegido\b/i.test(text) || /\bel escogido\b/i.test(text))) {
        flags.push("Rejected: ἐκλεκτῶν is plural — not 'el elegido/escogido'.");
      }
      if (item.number === "plural" && !/\b(elegidos|escogidos)\b/i.test(text)) {
        flags.push("Rejected: plural ἐκλεκτῶν must appear as elegidos/escogidos.");
      }
    }
  }

  if (/\bél es\b/i.test(text) || /\bella es\b/i.test(text)) {
    flags.push("Rejected: added subject/copula not in the Greek phrase.");
  }

  if (/salvación|camino para ser salvado|jesucristo es el elegido/i.test(text)) {
    flags.push("Rejected: theological addition beyond this phrase.");
  }

  // πιστεύω passive must not become "creer"
  const hasPistueoPassive = (analysis?.gates?.morphology?.constraints || []).some(item =>
    /πιστεύω/.test(item.lemma || "") && /passive/i.test(item.explanation || "")
  );
  if (hasPistueoPassive && /\b(creí|creyó|creído|creida|creiste)\b/i.test(text)) {
    flags.push("Rejected: πιστεύω passive means 'was entrusted', not 'believed'.");
  }

  if (/\bde nosotros\b/i.test(text) && /\b(salvador|señor|dios)\b/i.test(text)) {
    flags.push("Rejected: ἡμῶν should be possessive 'nuestro', not 'de nosotros'.");
  }

  if (/\btiempos escogidos\b/i.test(text)) {
    flags.push("Rejected: ἰδίοις means 'own/proper', not 'escogidos'.");
  }

  // RV1909 orthography bleed (preposition/article "á")
  if (/(?:^|\s)á(?:\s|$)/u.test(text) || /\sá[aeiouáéíóú]/iu.test(text)) {
    flags.push("Rejected: archaic RV1909 orthography (á); use contemporary Spanish (a, de, etc.).");
  }

  if (/\bvarones\b/i.test(text) && /ἀνήρ|ἀνδρ/u.test(JSON.stringify(analysis?.gates?.morphology?.constraints || []))) {
    // Household context: ἰδίοις ἀνδράσιν → maridos, not generic 'varones'
    const hasIdiois = (analysis?.gates?.morphology?.constraints || []).some(item =>
      /ἴδιος|ἰδίοις|ἰδίους/u.test(item.greek || "") || /ἴδιος/.test(item.lemma || "")
    );
    if (hasIdiois) {
      flags.push("Rejected: ἰδίοις ἀνδράσιν in household context → 'sus propios maridos', not 'varones'.");
    }
  }

  // Servant fidelity: πίστις + ἐνδείκνυμι / δοῦλος discourse → not bare "fe"
  const constraints = analysis?.gates?.morphology?.constraints || [];
  const hasPistis = constraints.some(item => (item.lemma || "") === "πίστις");
  const hasEndeiknumi = constraints.some(item => /ἐνδείκνυμ/.test(item.lemma || ""));
  if (hasPistis && hasEndeiknumi && /\bfe\b/i.test(text) && !/\b(fidelidad|lealtad)\b/i.test(text)) {
    flags.push("Rejected: πίστιν … ἐνδεικνυμένους in servant context → fidelidad/lealtad, not 'fe'.");
  }

  const greek = String(analysis?.greek || "");
  if (/^Ταῦτα\b/u.test(greek) && /\bEste\b/.test(text)) {
    flags.push("Rejected: Ταῦτα is neuter plural → 'Estas cosas'/'Esto', not 'Este'.");
  }
  if (/παρακάλει/u.test(greek) && /\bruega\b/i.test(text)) {
    flags.push("Rejected: παρακάλει (pastoral) → 'exhorta', not 'ruega'.");
  }
  if (/Πιστὸς\s+ὁ\s+λόγος/u.test(greek) && !/\b(fiel|fiable)\b/i.test(text)) {
    flags.push("Rejected: Πιστὸς ὁ λόγος → 'Fiel es la palabra' / 'Palabra fiel'.");
  }
  if (/Πιστὸς\s+ὁ\s+λόγος/u.test(greek) && /\bfiest/i.test(text)) {
    flags.push("Rejected: hallucinated 'fiesta' for Πιστὸς ὁ λόγος.");
  }
  if (/φιλανθρωπία/u.test(greek) && /\bhumanidad\b/i.test(text) && !/\bamor\b/i.test(text)) {
    flags.push("Rejected: φιλανθρωπία → 'amor a los hombres', not bare 'humanidad'.");
  }
  if (/Ἰησοῦ\s+Χριστοῦ/u.test(greek) && /\bJesús\b/i.test(text) && !/\bCristo\b/i.test(text)) {
    flags.push("Rejected: Greek has Ἰησοῦ Χριστοῦ — keep Jesucristo / Jesús Cristo.");
  }
  // Spillover: if this phrase is a short imperative clause, reject long multi-clause dumps
  const tokenCount = (analysis?.gates?.morphology?.constraints || []).length;
  if (tokenCount > 0 && tokenCount <= 6 && (text.match(/,/g) || []).length >= 3 && /\b(Nicópolis|Artemas|Tíquico)\b/i.test(text)) {
    const hasOnlyTravelSetup = /Ὅταν\s+πέμψω/u.test(greek);
    const hasComeImperative = /σπούδασον\s+ἐλθεῖν/u.test(greek);
    if (hasOnlyTravelSetup && /\bvenir\b/i.test(text) && /\bNicópolis\b/i.test(text)) {
      flags.push("Rejected: phrase spillover — travel setup must not include 'venir a Nicópolis' from the next span.");
    }
    if (hasComeImperative && /\bArtemas\b/i.test(text)) {
      flags.push("Rejected: phrase spillover — 'venir' span must not include Artemas/Tíquico from the previous span.");
    }
  }
  if (/μανθανέτωσαν/.test(greek) && /προΐστασθαι/.test(greek) && !/ἄκαρποι/u.test(greek)) {
    if (/\b(sin fruto|inútiles)\b/i.test(text)) {
      flags.push("Rejected: phrase spillover — do not pull ἵνα μὴ ὦσιν ἄκαρποι into the μανθανέτωσαν span.");
    }
  }
  if (/Ἀσπάζοντα[ίι]\s+σε/u.test(greek) && !/\bte\b/i.test(text)) {
    flags.push("Rejected: Ἀσπάζονταί σε requires object 'te'.");
  }
  if (/ἡ\s+χάρις\s+μετὰ\s+πάντων\s+ὑμῶν/u.test(greek) && !/\btodos\b/i.test(text)) {
    flags.push("Rejected: ἡ χάρις μετὰ πάντων ὑμῶν must keep 'todos'.");
  }
  if (/καλῶν\s+ἔργων\s+προΐστασθαι/u.test(greek)
    && !/\b(dedic|ocup|gobern)/i.test(text)
    && /\baprend/i.test(text)) {
    flags.push("Rejected: καλῶν ἔργων προΐστασθαι → dedicarse/ocuparse en buenas obras, not only 'aprender de'.");
  }

  return { ok: flags.length === 0, flags };
}

export async function assistPhraseGates({
  rootDir,
  analysis,
  rv1909Text = ""
}) {
  const availability = await describeAiAvailability();
  if (!availability.available) {
    const error = new Error(availability.message || "AI assist unavailable");
    error.code = "AI_NOT_CONFIGURED";
    throw error;
  }

  if (!analysis.readyForSynthesis) {
    const investigationId = analysis?.gates?.lemma?.investigationId || "the open investigation";
    const sourceVariant = analysis?.gates?.lemma?.blockReason === "source-variant";
    return {
      provider: availability.provider,
      model: availability.model,
      draftSource: "blocked",
      gateSummaries: {},
      proposedSpanish: null,
      slots: [],
      template: null,
      rationale: [],
      blockedNote: sourceVariant
        ? `Drafting is withheld until a named human resolves ${investigationId}'s source-reading decision.`
        : `Gate 1 is blocked by ${investigationId}. Resolve the investigation before drafting.`,
      flags: ["No AI request was made while deterministic gates were blocked."],
      readyForSynthesis: false,
      pipelineStatus: analysis.pipelineStatus
    };
  }

  const mechanical = analysis.mechanicalDraft;
  const rulesMarkdown = await loadTranslationRules(rootDir);
  const prompt = buildTranslatePrompt({
    analysis,
    rulesMarkdown,
    rv1909Text: rv1909Text || analysis.gates?.rv1909Review?.rv1909Text || ""
  });

  const raw = await runChatCompletion({
    prompt,
    json: true,
    system: `You are a suggestion-only Bible translation assistant for LPF.
Produce faithful contemporary Spanish from the supplied Hebrew, Aramaic, or Greek source constraints.
Prefer natural modern Spanish that a human can usually accept with light edits.
Never copy a mechanical word-by-word gloss as though it were Spanish. Never invent theology or violate source grammar.
You do not verify, approve, save, or publish translations. A named human decides every wording.
Return JSON only.`
  });

  const parsed = extractJsonObject(raw) || {};
  const gateSummaries = parsed.gateSummaries && typeof parsed.gateSummaries === "object"
    ? parsed.gateSummaries
    : {};
  const flags = Array.isArray(parsed.flags)
    ? parsed.flags.map(item => String(item).trim()).filter(Boolean)
    : [];

  let proposedSpanish = analysis.readyForSynthesis
    ? cleanProposal(parsed.proposedSpanish || "")
    : null;
  let draftSource = "ai";

  if (analysis.readyForSynthesis) {
    const validation = validateDraftAgainstGates(proposedSpanish, analysis, parsed.rationale);
    if (!proposedSpanish || !validation.ok) {
      flags.push(...validation.flags);
      proposedSpanish = null;
      draftSource = "rejected";
      flags.push("No draft was offered. The mechanical gloss remains diagnostic evidence only.");
    }
  }

  return {
    provider: availability.provider,
    model: availability.model,
    draftSource,
    gateSummaries: {
      lemma: scrubSummary(gateSummaries.lemma),
      morphology: scrubSummary(gateSummaries.morphology),
      immediateContext: scrubSummary(gateSummaries.immediateContext),
      generalContext: scrubSummary(gateSummaries.generalContext),
      rv1909Review: scrubSummary(gateSummaries.rv1909Review)
    },
    proposedSpanish,
    slots: mechanical?.slots || [],
    template: mechanical?.template || null,
    rationale: Array.isArray(parsed.rationale)
      ? parsed.rationale.map(item => String(item).trim()).filter(Boolean)
      : [],
    blockedNote: parsed.blockedNote ? String(parsed.blockedNote).trim() : (
      analysis.pipelineStatus === "blocked"
        ? `Gate 1 blocked on ${analysis.constraints.blockedLemma || "lemma policy"}. Open an investigation before drafting.`
        : null
    ),
    flags,
    readyForSynthesis: analysis.readyForSynthesis,
    pipelineStatus: analysis.pipelineStatus
  };
}
