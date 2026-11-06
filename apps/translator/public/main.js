import {
  mapReverseLinksByTranslationPhrase,
  pendingAlignmentWorkItems
} from "./alignmentWorkflow.js";

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

function bookIdFromLocation() {
  const params = new URLSearchParams(window.location.search);
  return (params.get("book") || "titus").trim().toLowerCase() || "titus";
}

const state = {
  view: "translation",
  bookId: bookIdFromLocation(),
  investigation: "INV-56-0001",
  tab: tabs[0],
  phraseIndex: 0,
  selectedGreekKey: "G1401",
  evidenceFile: null,
  decision: null,
  translationReturn: null,
  translationLoadedFromDisk: false,
  translationDirty: false,
  translationSaveTimer: null,
  translationSaving: false,
  reverseLinksByPhrase: new Map(),
  reverseLinksMeta: null,
  activeReverseUnitId: null,
  workflow: null,
  workflowBusy: false,
  approvalStage: null,
  commitBusy: false,
  publishBusy: false,
  publicationResult: null,
  alignmentEditTokenIds: new Set(),
  dirty: false,
  saving: false
};

// Deterministic source-token links read from investigation evidence. These
// links identify the investigation for an exact OSHB token; they do not imply
// that the token has been aligned to any particular Spanish word.
const sourceInvestigationByOshbId = new Map();

const translationView = document.querySelector("#translation-view");
const finalizationView = document.querySelector("#finalization-view");
const investigationView = document.querySelector("#investigation-view");
const sidebar = document.querySelector(".sidebar");
const phraseInterlinear = document.querySelector("#phrase-interlinear");
const decisionPanel = document.querySelector("#decision-panel");
const decisionPanelLemma = document.querySelector("#decision-panel-lemma");
const decisionPanelPolicy = document.querySelector("#decision-panel-policy");
const decisionPanelStatus = document.querySelector("#decision-panel-status");
const decisionPanelSpanish = document.querySelector("#decision-panel-spanish");
const openInvestigationButton = document.querySelector("#open-investigation");
const investigationList = document.querySelector("#investigation-list");
const investigationToggle = document.querySelector("#investigation-toggle");
const newInvestigationButton = document.querySelector("#new-investigation");
const newInvestigationModal = document.querySelector("#new-investigation-modal");
const newInvLemma = document.querySelector("#new-inv-lemma");
const newInvStrongs = document.querySelector("#new-inv-strongs");
const newInvReference = document.querySelector("#new-inv-reference");
const newInvestigationMessage = document.querySelector("#new-investigation-message");
const createNewInvestigationButton = document.querySelector("#create-new-investigation");
const cancelNewInvestigationButton = document.querySelector("#cancel-new-investigation");
const title = document.querySelector("#investigation-title");
const metaPrimarySubject = document.querySelector("#meta-primary-subject");
const metaOriginReference = document.querySelector("#meta-origin-reference");
const metaCurrentStatus = document.querySelector("#meta-current-status");
const tabBar = document.querySelector("#tabs");
const editor = document.querySelector("#editor");
const evidenceViewer = document.querySelector("#evidence-viewer");
const decisionEditor = document.querySelector("#decision-editor");
const decisionStatus = document.querySelector("#decision-status");
const decisionVersion = document.querySelector("#decision-version");
const decisionEffectiveDate = document.querySelector("#decision-effective-date");
const decisionLemma = document.querySelector("#decision-lemma");
const decisionStrongs = document.querySelector("#decision-strongs");
const decisionRendering = document.querySelector("#decision-rendering");
const decisionConfidence = document.querySelector("#decision-confidence");
const decisionReason = document.querySelector("#decision-reason");
const decisionScope = document.querySelector("#decision-scope");
const decisionScopeReference = document.querySelector("#decision-scope-reference");
const decisionScopeCondition = document.querySelector("#decision-scope-condition");
const decisionApprovalAuthority = document.querySelector("#decision-approval-authority");
const decisionApprovedBy = document.querySelector("#decision-approved-by");
const decisionApprovedAt = document.querySelector("#decision-approved-at");
const approveDecision = document.querySelector("#approve-decision");
const translationEditor = document.querySelector("#translation-editor");
const spanishUnits = document.querySelector("#spanish-units");
const reverseLinksMeta = document.querySelector("#reverse-links-meta");
const translationReferenceTitle = document.querySelector("#translation-reference-title");
const translationReferenceMeta = document.querySelector("#translation-reference-meta");
const suggestionSourceLabel = document.querySelector("#suggestion-source-label");
const phraseSaveStatus = document.querySelector("#phrase-save-status");
const rv1909ReferenceText = document.querySelector("#rv1909-reference-text");
const bleReferenceText = document.querySelector("#ble-reference-text");
const pipelineMeta = document.querySelector("#pipeline-meta");
const gateStatusList = document.querySelector("#gate-status-list");
const pipelineBlockNote = document.querySelector("#pipeline-block-note");
const grammarSlots = document.querySelector("#grammar-slots");
const analyzeGatesButton = document.querySelector("#analyze-gates");
const assistGatesButton = document.querySelector("#assist-gates");
const openGateInvestigationButton = document.querySelector("#open-gate-investigation");
const openInvestigationsMenuButton = document.querySelector("#open-investigations-menu");
const openFinalizationButton = document.querySelector("#open-finalization");
const closeFinalizationButton = document.querySelector("#close-finalization");
const finalizationBookTitle = document.querySelector("#finalization-book-title");
const constrainedDraftText = document.querySelector("#constrained-draft-text");
const draftTemplate = document.querySelector("#draft-template");
const draftMeta = document.querySelector("#draft-meta");
const draftRationale = document.querySelector("#draft-rationale");
const acceptDraftButton = document.querySelector("#accept-draft");
const versePreviewText = document.querySelector("#verse-preview-text");
const previousPhrase = document.querySelector("#previous-phrase");
const nextPhrase = document.querySelector("#next-phrase");
const bookSelect = document.querySelector("#book-select");
const referenceJumpForm = document.querySelector("#reference-jump-form");
const referenceJumpInput = document.querySelector("#reference-jump-input");
const referenceJumpStatus = document.querySelector("#reference-jump-status");
const workflowSummary = document.querySelector("#workflow-summary");
const workflowOutput = document.querySelector("#workflow-output");
const workflowTranslationState = document.querySelector("#workflow-translation-state");
const workflowAlignmentState = document.querySelector("#workflow-alignment-state");
const workflowCommitState = document.querySelector("#workflow-commit-state");
const workflowExportState = document.querySelector("#workflow-export-state");
const workflowPublishState = document.querySelector("#workflow-publish-state");
const workflowPublicationState = document.querySelector("#workflow-publication-state");
const continueAlignmentButton = document.querySelector("#continue-alignment");
const verifyTranslationButton = document.querySelector("#verify-translation");
const approveTranslationButton = document.querySelector("#approve-translation");
const verifyAlignmentButton = document.querySelector("#verify-alignment");
const approveAlignmentButton = document.querySelector("#approve-alignment");
const reviewCommitButton = document.querySelector("#review-commit");
const exportBookButton = document.querySelector("#export-book");
const publishBookButton = document.querySelector("#publish-book");
const workflowApprovalModal = document.querySelector("#workflow-approval-modal");
const workflowApprovalTitle = document.querySelector("#workflow-approval-title");
const workflowApprovalCopy = document.querySelector("#workflow-approval-copy");
const workflowApproverName = document.querySelector("#workflow-approver-name");
const workflowHumanConfirmation = document.querySelector("#workflow-human-confirmation");
const workflowConfirmationCopy = document.querySelector("#workflow-confirmation-copy");
const workflowApprovalMessage = document.querySelector("#workflow-approval-message");
const cancelWorkflowApproval = document.querySelector("#cancel-workflow-approval");
const confirmWorkflowApproval = document.querySelector("#confirm-workflow-approval");
const workflowCommitModal = document.querySelector("#workflow-commit-modal");
const workflowCommitFiles = document.querySelector("#workflow-commit-files");
const workflowCommitMessage = document.querySelector("#workflow-commit-message");
const workflowCommitConfirmation = document.querySelector("#workflow-commit-confirmation");
const workflowCommitMessageText = document.querySelector("#workflow-commit-message-text");
const cancelWorkflowCommit = document.querySelector("#cancel-workflow-commit");
const confirmWorkflowCommit = document.querySelector("#confirm-workflow-commit");
const workflowPublishModal = document.querySelector("#workflow-publish-modal");
const workflowPublishDestination = document.querySelector("#workflow-publish-destination");
const workflowPublishConfirmation = document.querySelector("#workflow-publish-confirmation");
const workflowPublishMessage = document.querySelector("#workflow-publish-message");
const cancelWorkflowPublish = document.querySelector("#cancel-workflow-publish");
const confirmWorkflowPublish = document.querySelector("#confirm-workflow-publish");
const publicationHandoff = document.querySelector("#publication-handoff");
const publicationPushCommand = document.querySelector("#publication-push-command");
const copyPublicationCommand = document.querySelector("#copy-publication-command");
const publicationPrLink = document.querySelector("#publication-pr-link");
const publicationCopyStatus = document.querySelector("#publication-copy-status");
const alignmentEditor = document.querySelector("#alignment-editor");
const alignmentReference = document.querySelector("#alignment-reference");
const alignmentProgress = document.querySelector("#alignment-progress");
const alignmentSpanishContext = document.querySelector("#alignment-spanish-context");
const alignmentUnitLabel = document.querySelector("#alignment-unit-label");
const cancelAlignmentEdit = document.querySelector("#cancel-alignment-edit");
const saveAlignmentEdit = document.querySelector("#save-alignment-edit");
const confirmAlignmentPhrase = document.querySelector("#confirm-alignment-phrase");
const saveStatus = document.querySelector("#save-status");
const saveButton = document.querySelector("#save-button");
const gatherEvidence = document.querySelector("#gather-evidence");
const backToTranslation = document.querySelector("#back-to-translation");
const prototypeMessage = document.querySelector("#prototype-message");
const evidenceFiles = document.querySelector("#evidence-files");
const gatherModal = document.querySelector("#gather-modal");
const gatherMessage = document.querySelector("#gather-message");
const runGather = document.querySelector("#run-gather");
const cancelGather = document.querySelector("#cancel-gather");
const replaceActions = document.querySelector("#replace-actions");
const replaceMessage = document.querySelector("#replace-message");
const replaceEvidence = document.querySelector("#replace-evidence");
const cancelReplace = document.querySelector("#cancel-replace");

const defaultTranslationPhrases = [
  {
    reference: "Titus 1:1",
    greek: [
      { text: "Παῦλος" },
      { text: "δοῦλος", key: "doulos", strongs: "G1401", lemma: "δοῦλος" },
      { text: "θεοῦ" }
    ],
    prefix: "Pablo ",
    placeholder: "________",
    suffix: " de Dios",
    decisionStrong: "G1401",
    investigationId: "INV-56-0001",
    sourceTokenIds: ["n56001001001", "n56001001002", "n56001001003"],
    rv1909Text: "PABLO, siervo de Dios",
    bleText: "Pablo siervo de Dios",
    workingText: "",
    suggestionSource: "blank"
  },
  {
    reference: "Titus 1:1",
    greek: [
      { text: "ἀπόστολος", key: "apostolos", strongs: "G652", lemma: "ἀπόστολος" },
      { text: "δὲ" },
      { text: "Ἰησοῦ" },
      { text: "Χριστοῦ" }
    ],
    prefix: "",
    placeholder: "________",
    suffix: " de Jesucristo",
    decisionStrong: "G652",
    investigationId: "INV-56-0002",
    sourceTokenIds: ["n56001001004", "n56001001005", "n56001001006", "n56001001007"],
    rv1909Text: "y apóstol de Jesucristo",
    bleText: "apóstol de Jesucristo",
    workingText: "",
    suggestionSource: "blank",
    provisional: true
  },
  {
    reference: "Titus 1:1",
    greek: [
      { text: "κατὰ" },
      { text: "πίστιν", key: "pistis", strongs: "G4102", lemma: "πίστις", rmac: "N-ASF" },
      { text: "ἐκλεκτῶν" },
      { text: "θεοῦ" }
    ],
    prefix: "según ",
    placeholder: "________",
    suffix: " elegidos de Dios",
    decisionStrong: "G4102",
    investigationId: "INV-56-0003",
    sourceTokenIds: ["n56001001008", "n56001001009", "n56001001010", "n56001001011"],
    rv1909Text: "según la fe de los escogidos de Dios",
    bleText: "según fe elegidos de Dios",
    workingText: "",
    suggestionSource: "blank",
    provisional: true
  },
  {
    reference: "Titus 1:1",
    greek: [
      { text: "καὶ" },
      { text: "ἐπίγνωσιν" },
      { text: "ἀληθείας" }
    ],
    prefix: "",
    placeholder: "________",
    suffix: "",
    decisionStrong: "",
    investigationId: "",
    sourceTokenIds: ["n56001001012", "n56001001013", "n56001001014"],
    rv1909Text: "y el conocimiento de la verdad",
    bleText: "y conocimiento verdad",
    workingText: "",
    suggestionSource: "blank",
    provisional: true
  },
  {
    reference: "Titus 1:1",
    greek: [
      { text: "τῆς" },
      { text: "κατ’" },
      { text: "εὐσέβειαν" }
    ],
    prefix: "",
    placeholder: "________",
    suffix: "",
    decisionStrong: "",
    investigationId: "",
    sourceTokenIds: ["n56001001015", "n56001001016", "n56001001017"],
    rv1909Text: "que es según la piedad",
    bleText: "de la según piedad",
    workingText: "",
    suggestionSource: "blank",
    provisional: true
  }
];
let translationPhrases = structuredClone(defaultTranslationPhrases);
const phraseSeparator = " ";
let translationUnits = [];
let translationUnitsLoaded = false;
const pipelineCache = new Map();
let pipelineRequestId = 0;
let aiAvailability = { available: false, message: "Checking AI…" };

const greekKeyByStrong = {
  G1401: "G1401",
  G652: "G652",
  G4102: "G4102"
};

const greekWordInfo = {
  G1401: {
    lemma: "δοῦλος",
    strongs: "G1401",
    investigationId: "INV-56-0001",
    approved: false,
    rendering: "siervo",
    source: "BLE",
    reference: "Titus 1:1",
    surface: "δοῦλος"
  },
  G652: {
    lemma: "ἀπόστολος",
    strongs: "G652",
    investigationId: "INV-56-0002",
    approved: false,
    rendering: "apóstol",
    source: "BLE",
    reference: "Titus 1:1",
    surface: "ἀπόστολος"
  },
  G4102: {
    lemma: "πίστις",
    strongs: "G4102",
    investigationId: "INV-56-0003",
    approved: false,
    rendering: "fe",
    source: "BLE",
    reference: "Titus 1:1",
    surface: "πίστιν",
    rmac: "N-ASF",
    construction: {
      prepositionSurface: "κατὰ",
      prepositionLemma: "κατά",
      caseCode: "A"
    }
  }
};

function selectedGreekInfo() {
  return greekWordInfo[state.selectedGreekKey]
    || Object.values(greekWordInfo).find(info => info.investigationId === state.investigation)
    || greekWordInfo.G1401;
}

function greekWordKey({ strongs = "", lemma = "", surface = "" } = {}) {
  const normalizedStrongs = String(strongs || "").trim().toUpperCase();
  if (normalizedStrongs) return normalizedStrongs;
  if (lemma) return `lemma:${lemma}`;
  if (surface) return `surface:${surface}`;
  return "";
}

function linkInvestigationToWordInfo({ lemma = "", strongs = "", investigationId = "", approved = false, rendering = "", source = "" } = {}) {
  const key = greekWordKey({ strongs, lemma });
  if (!key) return null;
  const existing = greekWordInfo[key] || {};
  greekWordInfo[key] = {
    ...existing,
    lemma: lemma || existing.lemma || "",
    strongs: String(strongs || existing.strongs || "").toUpperCase(),
    investigationId: investigationId || existing.investigationId || "",
    approved: approved || existing.approved || false,
    rendering: rendering || existing.rendering || "",
    source: source || existing.source || "BLE",
    reference: existing.reference || currentPhrase()?.reference || "Titus 1:1",
    surface: existing.surface || lemma || ""
  };
  if (greekWordInfo[key].strongs) {
    greekKeyByStrong[greekWordInfo[key].strongs] = key;
  }
  return key;
}

function registerTokenAsGreekWord(token = {}) {
  const surface = token.greek || token.surface || "";
  const lemma = token.lemma || surface || "";
  const strongs = String(token.strongs || "").trim().toUpperCase();
  const key = greekWordKey({ strongs, lemma, surface });
  if (!key) return "";

  const existing = greekWordInfo[key]
    || Object.values(greekWordInfo).find(info =>
      (strongs && info.strongs === strongs)
      || (lemma && info.lemma === lemma)
      || (surface && info.surface === surface)
    )
    || {};

  const language = token.lang === "arc" || token.lang === "he" || isHebrewStrongs(strongs)
    ? "hebrew"
    : (existing.language || "greek");

  greekWordInfo[key] = {
    ...existing,
    lemma: lemma || existing.lemma || "",
    strongs: strongs || existing.strongs || "",
    investigationId: sourceInvestigationByOshbId.get(token.oshbId)
      || existing.investigationId
      || "",
    approved: existing.approved || false,
    rendering: existing.rendering || token.ble || token.es || "",
    source: existing.source || "BLE",
    reference: currentPhrase()?.reference || existing.reference || "Titus 1:1",
    surface: surface || existing.surface || lemma,
    rmac: token.rmac || token.morph || existing.rmac || "",
    sourceTokenId: token.sourceTokenId || existing.sourceTokenId || "",
    oshbId: token.oshbId || existing.oshbId || "",
    language,
    construction: existing.construction
  };
  if (greekWordInfo[key].strongs) {
    greekKeyByStrong[greekWordInfo[key].strongs] = key;
  }
  return key;
}

function currentPhrase() {
  return translationPhrases[state.phraseIndex];
}

function defaultTranslationDocument() {
  return translationPhrases.map(phrase => phraseDisplayText(phrase)).filter(Boolean).join(phraseSeparator);
}

function phraseGreekText(phrase) {
  const fromTokens = (phrase?.tokenRows || []).map(row => row.greek).filter(Boolean).join(" ");
  if (fromTokens) return fromTokens;
  if (Array.isArray(phrase?.greek)) {
    return phrase.greek.map(token => token.text).join(" ");
  }
  return String(phrase?.greek || "").trim();
}

function phraseBleText(phrase) {
  const fromTokens = (phrase?.tokenRows || []).map(row => row.ble).filter(Boolean).join(" ");
  return fromTokens || String(phrase?.bleText || "").trim();
}

function phraseRv1909Text(phrase) {
  // Prefer phrase-aligned RV1909 span (keeps articles/punctuation).
  // Per-token rv1909 fragments are for interlinear only and are not faithful spans.
  const aligned = String(phrase?.rv1909Text || "").trim();
  if (aligned) return aligned;
  return (phrase?.tokenRows || []).map(row => row.rv1909).filter(Boolean).join(" ");
}

function setPhraseSaveStatus(text, stateName = "saved") {
  phraseSaveStatus.textContent = text;
  phraseSaveStatus.dataset.state = stateName;
}

function phraseDisplayText(phrase) {
  return String(phrase.workingText ?? phrase.savedText ?? "").trim();
}

function isTranslationDirty() {
  syncTranslationDocumentFromEditor();
  return translationPhrases.some(phrase =>
    String(phrase.workingText || "").trim() !== String(phrase.savedText || "").trim()
  );
}

function markTranslationDirty() {
  state.translationDirty = true;
  setPhraseSaveStatus("Unsaved changes", "dirty");
}

function serializePhraseRecords() {
  syncTranslationDocumentFromEditor();
  return translationPhrases.map((phrase, index) => {
    const canonical = defaultTranslationPhrases[index];
    const sourceTokenIds = canonical?.sourceTokenIds?.length
      ? canonical.sourceTokenIds
      : (phrase.sourceTokenIds || []);

    return {
      reference: phrase.reference,
      phraseIndex: index,
      greek: phraseGreekText(canonical || phrase),
      spanish: phraseDisplayText(phrase),
      sourceTokenIds,
      tokenRows: phrase.tokenRows || [],
      rv1909Text: phraseRv1909Text(phrase) || phrase.rv1909Text || canonical?.rv1909Text || "",
      bleText: phraseBleText(phrase) || phrase.bleText || canonical?.bleText || "",
      suggestionSource: phrase.suggestionSource || ""
    };
  });
}

function suggestionSourceFromRecord(record, savedText) {
  const source = String(record?.suggestionSource || "").trim();
  if (source) return source;
  if (!savedText) return "blank";
  return "lbf-preliminary";
}

function makePhraseFromRecord(record) {
  const rv1909Text = String(record.rv1909Text || "");
  const bleText = String(record.bleText || "");
  const savedText = String(record.spanish || "");
  return {
    phraseIndex: Number(record.phraseIndex),
    reference: record.reference || "Titus 1:1",
    greek: [{ text: record.greek || record.reference || "" }],
    prefix: "",
    placeholder: "________",
    suffix: "",
    decisionStrong: "",
    investigationId: "",
    sourceTokenIds: Array.isArray(record.sourceTokenIds) ? record.sourceTokenIds : [],
    tokenRows: Array.isArray(record.tokenRows) ? record.tokenRows : [],
    rv1909Text,
    bleText,
    savedText,
    workingText: savedText,
    suggestionSource: suggestionSourceFromRecord(record, savedText),
    provisional: true
  };
}

function phraseRecordKey(record) {
  return `${record.reference || ""}|${Number(record.phraseIndex)}`;
}

function canonicalPhraseRecordKey(phrase, index) {
  return `${phrase.reference || ""}|${index}`;
}

function mergeSavedRecord(base, record, { preserveStructure = false } = {}) {
  if (!record) {
    return structuredClone(base);
  }

  const savedText = String(record.spanish || "");
  const rv1909Text = String(record.rv1909Text || base.rv1909Text || "");
  const bleText = String(record.bleText || base.bleText || "");

  if (preserveStructure) {
    return {
      ...structuredClone(base),
      phraseIndex: Number(record.phraseIndex),
      sourceTokenIds: Array.isArray(record.sourceTokenIds) && record.sourceTokenIds.length
        ? record.sourceTokenIds
        : (base.sourceTokenIds || []),
      tokenRows: Array.isArray(record.tokenRows) && record.tokenRows.length
        ? record.tokenRows
        : (base.tokenRows || []),
      rv1909Text: rv1909Text || base.rv1909Text,
      bleText: bleText || base.bleText,
      savedText,
      workingText: savedText,
      suggestionSource: suggestionSourceFromRecord(record, savedText)
    };
  }

  return {
    ...structuredClone(base),
    phraseIndex: Number(record.phraseIndex),
    reference: record.reference || base.reference || "Titus 1:1",
    sourceTokenIds: Array.isArray(record.sourceTokenIds) && record.sourceTokenIds.length
      ? record.sourceTokenIds
      : (base.sourceTokenIds || []),
    tokenRows: Array.isArray(record.tokenRows) && record.tokenRows.length
      ? record.tokenRows
      : (base.tokenRows || []),
    rv1909Text,
    bleText,
    savedText,
    workingText: savedText,
    suggestionSource: suggestionSourceFromRecord(record, savedText)
  };
}

function resetTranslationPhrases() {
  translationPhrases = structuredClone(defaultTranslationPhrases).map((phrase, phraseIndex) => ({
    ...phrase,
    phraseIndex
  }));
}

function suggestionSourceForPhrase(phrase) {
  if (phrase.approvedDecision) return "Approved LBF decision";
  if (phrase.workingText && phrase.suggestionSource === "saved") return "Saved LBF phrase";
  if (phrase.workingText && phrase.suggestionSource === "lbf-preliminary") {
    return "Preliminary LBF draft — edit and save";
  }
  if (phrase.workingText && phrase.suggestionSource === "lbf-approved") return "Approved LBF phrase";
  if (phrase.workingText && phrase.suggestionSource === "ai-proposed") {
    return "Constrained AI draft (edit before saving)";
  }
  return "Fresh LBF translation";
}

async function loadAllTranslationUnits() {
  const { units } = await api(translationApiPath("/api/translation/units")).catch(() => ({ units: [] }));
  return Array.isArray(units) ? units : [];
}

async function loadContinuationUnits({ force = false } = {}) {
  if (translationUnitsLoaded && !force) return translationUnits;
  const units = await loadAllTranslationUnits();
  // Never permanently cache an empty failed load — retry next time.
  if (!units.length) {
    translationUnits = [];
    translationUnitsLoaded = false;
    return translationUnits;
  }
  translationUnits = units.filter(unit => unit.reference !== "Titus 1:1");
  translationUnitsLoaded = true;
  return translationUnits;
}

function makePhraseFromUnit(unit) {
  const rv1909Text = unit.rv1909Text || "";
  const bleText = unit.bleText || "";
  return {
    reference: unit.reference,
    greek: [{ text: unit.greekText || unit.reference }],
    prefix: "",
    placeholder: "________",
    suffix: "",
    decisionStrong: "",
    investigationId: "",
    sourceTokenIds: unit.sourceTokenIds || [],
    tokenRows: unit.tokenRows || [],
    rv1909Text,
    bleText,
    savedText: "",
    workingText: "",
    suggestionSource: "blank",
    provisional: true
  };
}

function hasMoreTranslationUnits() {
  // Prefer the saved phrase list from disk. Do not append blank whole-verse
  // units when we already have phrase-level rows for every available unit.
  if (!translationUnitsLoaded) return translationPhrases.length <= defaultTranslationPhrases.length;
  const queuedReferences = new Set(translationPhrases.map(phrase => phrase.reference));
  return translationUnits.some(unit => !queuedReferences.has(unit.reference));
}

async function appendNextTranslationUnit() {
  const canonicalCount = defaultTranslationPhrases.length;
  if (translationPhrases.length < canonicalCount) {
    return false;
  }

  // Never invent blank continuation phrases when disk already gave us a full book seed.
  if (translationPhrases.length > canonicalCount && !hasMoreTranslationUnits()) {
    return false;
  }

  const units = await loadContinuationUnits();
  if (!units.length) {
    await loadContinuationUnits({ force: true });
  }
  const queuedReferences = new Set(translationPhrases.map(phrase => phrase.reference));
  const unit = (translationUnits.length ? translationUnits : units)
    .find(item => !queuedReferences.has(item.reference));
  if (!unit) return false;

  const phrase = makePhraseFromUnit(unit);
  translationPhrases = [...translationPhrases, phrase];
  return true;
}

function currentPhraseKey(phrase = currentPhrase(), index = state.phraseIndex) {
  return `${phrase?.reference || ""}|${index}`;
}

const GATE_ORDER = [
  "lemma",
  "morphology",
  "immediateContext",
  "generalContext",
  "rv1909Review"
];

const GATE_MARK = {
  idle: "○",
  busy: "…",
  resolved: "✓",
  consulted: "✓",
  blocked: "✕"
};

function phrasePipelinePayload(phrase = currentPhrase()) {
  return {
    book: state.bookId,
    reference: phrase.reference,
    greek: phraseGreekText(phrase),
    tokenRows: phrase.tokenRows || [],
    rv1909Text: phraseRv1909Text(phrase),
    bleText: phraseBleText(phrase),
    priorLbf: priorLbfForSuggestion(phrase)
  };
}

function priorLbfForSuggestion(phrase = currentPhrase()) {
  // Prefer same-chapter approved/working phrases so Gate 4 sees local discourse.
  const currentRef = String(phrase?.reference || "");
  const chapterKey = currentRef.replace(/:\d+\s*$/u, ""); // "Titus 1"
  const sameChapter = translationPhrases.filter(item =>
    item !== phrase
    && phraseDisplayText(item)
    && String(item.reference || "").replace(/:\d+\s*$/u, "") === chapterKey
  );
  const pool = sameChapter.length
    ? sameChapter
    : translationPhrases.filter(item => item !== phrase && phraseDisplayText(item));

  return pool
    .slice(-12)
    .map(item => ({
      reference: item.reference,
      spanish: phraseDisplayText(item)
    }));
}

function resetPipelineUi() {
  pipelineMeta.textContent = "Analyze this phrase to begin";
  pipelineBlockNote.hidden = true;
  pipelineBlockNote.textContent = "";
  openGateInvestigationButton.hidden = true;
  openGateInvestigationButton.dataset.investigationId = "";
  assistGatesButton.disabled = true;
  assistGatesButton.textContent = "Propose Spanish";
  analyzeGatesButton.disabled = false;
  analyzeGatesButton.textContent = "Analyze phrase";
  constrainedDraftText.textContent = "Run Analyze, then Propose Spanish for a grammar-checked modern draft.";
  draftMeta.textContent = "Available after gates are ready";
  acceptDraftButton.disabled = true;
  draftRationale.hidden = true;
  draftRationale.innerHTML = "";
  if (draftTemplate) {
    draftTemplate.hidden = true;
    draftTemplate.textContent = "";
  }
  if (grammarSlots) {
    grammarSlots.hidden = true;
    grammarSlots.innerHTML = "";
  }
  for (const id of GATE_ORDER) {
    setGateRow(id, { status: "idle", detail: "—" });
  }
}

function renderGrammarSlots(slots = []) {
  if (!grammarSlots) return;
  const visible = (slots || []).filter(slot => !slot.omit);
  if (!visible.length) {
    grammarSlots.hidden = true;
    grammarSlots.innerHTML = "";
    return;
  }
  grammarSlots.hidden = false;
  grammarSlots.innerHTML = visible.map(slot => {
    const relation = slot.relation === "de"
      ? `de${slot.number === "plural" ? " los" : ""}`
      : (slot.role === "preposition" ? "prep" : "—");
    return `<div class="grammar-slot">
      <span class="grammar-slot-greek">${escapeHtml(slot.greek || "—")}</span>
      <span class="grammar-slot-morph">${escapeHtml(slot.morph || "—")}</span>
      <span class="grammar-slot-fill">${escapeHtml(relation)} → <strong>${escapeHtml(slot.value || "—")}</strong></span>
    </div>`;
  }).join("");
}

function setGateRow(gateId, { status = "idle", detail = "—" } = {}) {
  const row = gateStatusList?.querySelector(`[data-gate="${gateId}"]`);
  if (!row) return;
  const mark = row.querySelector(".gate-mark");
  const detailEl = row.querySelector(".gate-detail");
  if (mark) {
    mark.dataset.status = status;
    mark.textContent = GATE_MARK[status] || GATE_MARK.idle;
  }
  if (detailEl) detailEl.textContent = detail || "—";
}

function renderGateAnalysis(analysis, assist = null) {
  if (!analysis?.gates) {
    resetPipelineUi();
    return;
  }

  const summaries = assist?.gateSummaries || {};
  for (const id of GATE_ORDER) {
    const gate = analysis.gates[id];
    if (!gate) {
      setGateRow(id, { status: "idle", detail: "—" });
      continue;
    }
    const aiNote = summaries[id];
    let detail = [gate.summary, aiNote].filter(Boolean).join(" — ");
    if (id === "generalContext" && Array.isArray(gate.notes) && gate.notes.length) {
      const firstUseful = gate.notes.find(n => /Verse Greek|Same-verse|Local paragraph|Lemma «/u.test(n));
      if (firstUseful && !detail.includes(firstUseful.slice(0, 40))) {
        detail = [detail, firstUseful].filter(Boolean).join(" · ");
      }
    }
    setGateRow(id, { status: gate.status || "idle", detail });
  }

  const blocked = analysis.pipelineStatus === "blocked";
  pipelineMeta.textContent = blocked
    ? "Pipeline blocked at Gate 1 (lemma policy)"
    : analysis.readyForSynthesis
      ? "Gates ready for constrained draft"
      : "Gate analysis incomplete";

  if (blocked) {
    pipelineBlockNote.hidden = false;
    pipelineBlockNote.textContent = assist?.blockedNote
      || `No approved lemma policy for ${analysis.constraints?.blockedLemma || "this lemma"}. Open an investigation before drafting.`;
    const invId = analysis.constraints?.investigationId
      || analysis.gates?.lemma?.investigationId
      || "";
    openGateInvestigationButton.hidden = false;
    openGateInvestigationButton.dataset.investigationId = invId;
    openGateInvestigationButton.dataset.blockedLemma = analysis.constraints?.blockedLemmaForm
      || analysis.gates?.lemma?.blockedLemmaForm
      || "";
    openGateInvestigationButton.dataset.blockedStrongs = analysis.constraints?.blockedStrongs
      || analysis.gates?.lemma?.blockedStrongs
      || "";
    openGateInvestigationButton.textContent = invId
      ? `Open ${invId}`
      : "Start investigation";
  } else {
    pipelineBlockNote.hidden = true;
    pipelineBlockNote.textContent = "";
    openGateInvestigationButton.hidden = true;
  }

  assistGatesButton.disabled = false;
  const slots = assist?.slots || analysis.mechanicalDraft?.slots || [];
  renderGrammarSlots(slots);
  if (draftTemplate) {
    const template = assist?.template || analysis.mechanicalDraft?.template || "";
    draftTemplate.hidden = !template;
    draftTemplate.textContent = template ? `Template: ${template}` : "";
  }

  if (assist?.proposedSpanish) {
    constrainedDraftText.textContent = assist.proposedSpanish;
    const sourceLabel = `AI suggestion · ${assist.provider}/${assist.model}`;
    draftMeta.textContent = sourceLabel;
    acceptDraftButton.disabled = false;
    const rationale = Array.isArray(assist.rationale) ? assist.rationale : [];
    const flags = Array.isArray(assist.flags) ? assist.flags : [];
    const notes = [
      ...flags.map(flag => `Flag: ${flag}`),
      ...rationale
    ];
    if (notes.length) {
      draftRationale.hidden = false;
      draftRationale.innerHTML = notes.map(note => `<li>${escapeHtml(note)}</li>`).join("");
    } else {
      draftRationale.hidden = true;
      draftRationale.innerHTML = "";
    }
  } else if (assist?.draftSource === "rejected") {
    constrainedDraftText.textContent = "Suggestion rejected: the model did not produce usable grammatical Spanish.";
    draftMeta.textContent = `Rejected by deterministic checks · ${assist.provider}/${assist.model}`;
    acceptDraftButton.disabled = true;
    const flags = Array.isArray(assist.flags) ? assist.flags : [];
    draftRationale.hidden = flags.length === 0;
    draftRationale.innerHTML = flags.map(flag => `<li>${escapeHtml(flag)}</li>`).join("");
  } else if (blocked) {
    constrainedDraftText.textContent = "Draft withheld until Gate 1 is resolved.";
    draftMeta.textContent = "Blocked";
    acceptDraftButton.disabled = true;
    draftRationale.hidden = true;
  } else if (analysis.mechanicalDraft?.proposedSpanish) {
    constrainedDraftText.textContent = analysis.mechanicalDraft.proposedSpanish;
    draftMeta.textContent = "Diagnostic gloss stream only — cannot be used as a translation";
    acceptDraftButton.disabled = true;
    const notes = analysis.mechanicalDraft.notes || [];
    if (notes.length) {
      draftRationale.hidden = false;
      draftRationale.innerHTML = notes.map(note => `<li>${escapeHtml(note)}</li>`).join("");
    } else {
      draftRationale.hidden = true;
    }
  } else {
    constrainedDraftText.textContent = "Gates analyzed. Draft appears when Gate 1 is clear.";
    draftMeta.textContent = aiAvailability.available
      ? `${aiAvailability.provider}/${aiAvailability.model}`
      : (aiAvailability.message || "AI unavailable");
    acceptDraftButton.disabled = true;
    draftRationale.hidden = true;
  }
}

function applyPipelineCache(phrase = currentPhrase()) {
  const cached = pipelineCache.get(currentPhraseKey(phrase));
  if (!cached) {
    phrase.pipelineAnalysis = null;
    phrase.pipelineAssist = null;
    phrase.constrainedDraft = "";
    resetPipelineUi();
    return null;
  }
  phrase.pipelineAnalysis = cached.analysis || null;
  phrase.pipelineAssist = cached.assist || null;
  phrase.constrainedDraft = cached.assist?.proposedSpanish
    || "";
  renderGateAnalysis(cached.analysis, cached.assist || null);
  return cached;
}

async function loadAiAvailability() {
  aiAvailability = await api("/api/translation/ai").catch(() => ({
    available: false,
    message: "AI assist unavailable"
  }));
  return aiAvailability;
}

async function analyzeCurrentPhrase({ force = false } = {}) {
  const phrase = currentPhrase();
  const cacheKey = currentPhraseKey(phrase);
  const requestId = ++pipelineRequestId;

  if (!force && pipelineCache.has(cacheKey) && pipelineCache.get(cacheKey).analysis) {
    return applyPipelineCache(phrase);
  }

  analyzeGatesButton.disabled = true;
  analyzeGatesButton.textContent = "Analyzing…";
  assistGatesButton.disabled = true;
  for (const id of GATE_ORDER) {
    setGateRow(id, { status: "busy", detail: "Analyzing…" });
  }
  pipelineMeta.textContent = "Running mechanical gates…";

  try {
    const analysis = await api("/api/translation/gates", {
      method: "POST",
      body: JSON.stringify(phrasePipelinePayload(phrase))
    });

    if (requestId !== pipelineRequestId || currentPhraseKey() !== cacheKey) {
      return analysis;
    }

    const previous = pipelineCache.get(cacheKey) || {};
    const next = { ...previous, analysis, assist: null };
    pipelineCache.set(cacheKey, next);
    phrase.pipelineAnalysis = analysis;
    phrase.pipelineAssist = null;
    phrase.constrainedDraft = "";
    renderGateAnalysis(analysis, null);
    return next;
  } catch (error) {
    if (requestId !== pipelineRequestId || currentPhraseKey() !== cacheKey) return null;
    resetPipelineUi();
    pipelineMeta.textContent = error.message || "Gate analysis failed";
    prototypeMessage.textContent = error.message || "Gate analysis failed";
    return null;
  } finally {
    if (requestId === pipelineRequestId) {
      analyzeGatesButton.disabled = false;
      analyzeGatesButton.textContent = "Analyze phrase";
    }
  }
}

async function assistCurrentPhrase() {
  const phrase = currentPhrase();
  const cacheKey = currentPhraseKey(phrase);
  const requestId = ++pipelineRequestId;

  if (!aiAvailability.available) {
    draftMeta.textContent = aiAvailability.message || "AI unavailable";
    constrainedDraftText.textContent = "Start the configured local AI server to enable optional drafting suggestions.";
    return null;
  }

  assistGatesButton.disabled = true;
  assistGatesButton.textContent = "Proposing…";
  analyzeGatesButton.disabled = true;
  draftMeta.textContent = `${aiAvailability.provider}/${aiAvailability.model}`;
  constrainedDraftText.textContent = "Proposing modern Spanish under source-language grammar constraints…";
  acceptDraftButton.disabled = true;

  try {
    const result = await api("/api/translation/gates/assist", {
      method: "POST",
      body: JSON.stringify(phrasePipelinePayload(phrase))
    });

    if (requestId !== pipelineRequestId || currentPhraseKey() !== cacheKey) {
      return result;
    }

    pipelineCache.set(cacheKey, result);
    phrase.pipelineAnalysis = result.analysis;
    phrase.pipelineAssist = result.assist;
    phrase.constrainedDraft = result.assist?.proposedSpanish
      || "";
    renderGateAnalysis(result.analysis, result.assist);
    return result;
  } catch (error) {
    if (requestId !== pipelineRequestId || currentPhraseKey() !== cacheKey) return null;
    constrainedDraftText.textContent = error.message || "AI proposal failed";
    draftMeta.textContent = error.code || "error";
    acceptDraftButton.disabled = true;
    if (phrase.pipelineAnalysis?.mechanicalDraft?.proposedSpanish) {
      renderGateAnalysis(phrase.pipelineAnalysis, null);
    }
    prototypeMessage.textContent = error.message || "AI proposal failed";
    return null;
  } finally {
    if (requestId === pipelineRequestId) {
      analyzeGatesButton.disabled = false;
      assistGatesButton.disabled = false;
      assistGatesButton.textContent = "Propose Spanish";
    }
  }
}

function acceptConstrainedDraft() {
  const phrase = currentPhrase();
  const proposal = String(phrase.constrainedDraft || constrainedDraftText.textContent || "").trim();
  if (!proposal || proposal === "—" || /^(Run Analyze|Gates analyzed|Draft withheld|Start (?:Ollama|the configured)|Summarizing)/.test(proposal)) {
    return;
  }

  phrase.workingText = proposal;
  phrase.suggestionSource = "ai-proposed";
  translationEditor.value = proposal;
  markTranslationDirty();
  renderVersePreview();
  suggestionSourceLabel.textContent = "Constrained AI draft (edit before saving)";
  translationEditor.focus();
  placeTranslationCursor(proposal.length);
}

function firstIncompletePhraseIndex() {
  const index = translationPhrases.findIndex(phrase => !phraseDisplayText(phrase));
  // If every phrase already has preliminary Spanish, start at the beginning.
  return index >= 0 ? index : 0;
}

async function enrichPhraseReferencesFromUnits() {
  const units = await loadAllTranslationUnits();
  const unitsByReference = new Map(units.map(unit => [unit.reference, unit]));
  translationPhrases = translationPhrases.map(phrase => {
    const unit = unitsByReference.get(phrase.reference);
    if (!unit) return phrase;

    const sourceTokenIds = phrase.sourceTokenIds?.length
      ? phrase.sourceTokenIds
      : (unit.sourceTokenIds || []);
    const tokenIdSet = new Set(sourceTokenIds);
    const unitTokenRows = (unit.tokenRows || []).filter(row => tokenIdSet.has(row.sourceTokenId));
    const tokenRows = unitTokenRows.length ? unitTokenRows : (phrase.tokenRows || []);
    const greekFromTokens = tokenRows.map(row => row.greek).filter(Boolean).join(" ");
    const bleFromTokens = tokenRows.map(row => row.ble).filter(Boolean).join(" ");
    // Do not rebuild RV1909 from token fragments — that drops articles/punctuation.
    // Keep the phrase-aligned span from disk/API enrich.

    return {
      ...phrase,
      greek: greekFromTokens
        ? (Array.isArray(phrase.greek)
          ? tokenRows.map(row => ({ text: row.greek, ...(phrase.greek.find?.(t => t.text === row.greek) || {}) }))
          : greekFromTokens)
        : phrase.greek,
      sourceTokenIds,
      tokenRows,
      rv1909Text: phrase.rv1909Text || "",
      bleText: bleFromTokens || phrase.bleText || "",
      workingText: phrase.workingText || "",
      suggestionSource: phrase.workingText
        ? (phrase.suggestionSource || "lbf-preliminary")
        : "blank"
    };
  });
}

function buildTranslationLine(rendering = "") {
  const phrase = currentPhrase();
  const target = rendering || phrase.placeholder;
  return `${phrase.prefix}${target}${phrase.suffix}`;
}

function getTranslationTargetEnd(rendering = "") {
  const phrase = currentPhrase();
  return phrase.prefix.length + (rendering || phrase.workingText || phrase.placeholder).length;
}

function buildTranslationDocument() {
  return defaultTranslationDocument();
}

function getPhraseEnd(index = state.phraseIndex) {
  return translationPhrases[index].workingText.length;
}

function syncTranslationDocumentFromEditor() {
  currentPhrase().workingText = translationEditor.value;
}

function replacePhraseText(index, text) {
  translationPhrases[index].workingText = text;
  if (index === state.phraseIndex) {
    translationEditor.value = text;
  }
  renderVersePreview();
}

function scheduleTranslationSave() {
  markTranslationDirty();
}

async function saveTranslationDocument() {
  syncTranslationDocumentFromEditor();
  const phrase = currentPhrase();
  const previousSavedText = phrase.savedText || "";
  const previousSuggestionSource = phrase.suggestionSource || "";
  const nextSavedText = phrase.workingText;
  const spanishChanged = nextSavedText !== previousSavedText;

  phrase.savedText = nextSavedText;
  if (!nextSavedText.trim()) {
    phrase.suggestionSource = "blank";
  } else if (spanishChanged) {
    phrase.suggestionSource = "lbf-preliminary";
  }
  setPhraseSaveStatus("Saving...", "saving");
  state.translationSaving = true;
  try {
    await api(translationApiPath("/api/translation/current"), {
      method: "PUT",
      body: JSON.stringify({
        book: state.bookId,
        content: buildTranslationDocument(),
        phrases: serializePhraseRecords()
      })
    });
    translationPhrases.forEach(item => {
      item.savedText = item.workingText;
    });
    state.translationDirty = false;
    setPhraseSaveStatus("Saved", "saved");
    renderVersePreview();
    await loadBookWorkflow();
  } catch (error) {
    phrase.savedText = previousSavedText;
    phrase.suggestionSource = previousSuggestionSource;
    renderVersePreview();
    throw error;
  } finally {
    state.translationSaving = false;
  }
}

async function flushTranslationSave() {
  window.clearTimeout(state.translationSaveTimer);
  if (state.view !== "translation") return;
  if (!isTranslationDirty()) {
    state.translationDirty = false;
    setPhraseSaveStatus("Saved", "saved");
    return;
  }
  await saveTranslationDocument();
}

function translationApiPath(path) {
  const url = new URL(path, window.location.origin);
  url.searchParams.set("book", state.bookId || "titus");
  return `${url.pathname}?${url.searchParams.toString()}`;
}

function setWorkflowStep(id, status) {
  const element = document.querySelector(`#${id}`);
  if (element) element.dataset.status = status;
}

function showWorkflowOutput(text = "") {
  workflowOutput.textContent = text;
  workflowOutput.hidden = !text;
}

function renderBookWorkflow(payload) {
  if (!payload?.row) return;
  state.workflow = payload;
  const row = payload.row;
  const tr = row.translation;
  const al = row.alignment;
  const translationDone = tr === "done";
  const provenance = payload.provenance || {};
  const committed = provenance.committed === true;
  const exported = payload.export?.ready === true;
  const preparedThisSession = state.publicationResult?.book === state.bookId
    && state.publicationResult?.sourceCommit === payload.export?.sourceCommit;
  const branchPrepared = preparedThisSession || payload.publisher?.localBranchReady === true;
  const published = payload.publisher?.publishedToMain === true;
  const alignment = payload.progress?.alignment || {};
  const alignmentRemaining = (alignment.auto || 0)
    + (alignment.gloss || 0)
    + (alignment.unwalked || 0)
    + (alignment.unconfirmed || 0)
    + (alignment.other || 0);
  const alignmentDone = al === "done" && alignmentRemaining === 0;
  const finished = translationDone && alignmentDone;
  const editableUnitsRemaining = pendingAlignmentWork().length;

  workflowTranslationState.textContent = tr === "done"
    ? `Approved by ${row.translation_by} on ${row.translation_on}`
    : `${tr} · ${payload.progress?.verses || 0} verses`;
  workflowAlignmentState.textContent = alignmentDone
    ? `Approved by ${row.alignment_by} on ${row.alignment_on}`
    : `${alignmentRemaining ? "not ready" : al} · ${alignment.hand || 0} hand phrases, ${alignmentRemaining} phrases / ${editableUnitsRemaining} units remaining`;

  setWorkflowStep("workflow-translate", ["ready", "done"].includes(tr) ? "complete" : "active");
  setWorkflowStep("workflow-verify-translation", ["ready", "done"].includes(tr) ? "complete" : (tr === "draft" || tr === "none" ? "active" : "locked"));
  setWorkflowStep("workflow-approve-translation", translationDone ? "complete" : (tr === "ready" ? "active" : "locked"));
  setWorkflowStep("workflow-align", alignmentDone || (translationDone && alignmentRemaining === 0) ? "complete" : (translationDone ? "active" : "locked"));
  setWorkflowStep("workflow-verify-alignment", alignmentDone || (al === "ready" && alignmentRemaining === 0) ? "complete" : (translationDone && alignmentRemaining === 0 ? "active" : "locked"));
  setWorkflowStep("workflow-approve-alignment", alignmentDone ? "complete" : (translationDone && al === "ready" && alignmentRemaining === 0 ? "active" : "locked"));
  setWorkflowStep("workflow-commit", finished && committed ? "complete" : (finished ? "active" : "locked"));
  setWorkflowStep("workflow-export", exported ? "complete" : (finished && committed ? "active" : "locked"));
  setWorkflowStep("workflow-publish", branchPrepared || published ? "complete" : (exported ? "active" : "locked"));
  setWorkflowStep("workflow-publication", published ? "complete" : (branchPrepared ? "active" : "locked"));

  workflowCommitState.textContent = committed
    ? `Committed at ${provenance.sourceCommit || "HEAD"}`
    : finished
      ? `${provenance.changes?.length || 0} selected-book changes`
      : "Waiting for both approvals";
  workflowExportState.textContent = exported
    ? `Package ready at ${payload.export.packageDir}`
    : (payload.export?.problem || "Waiting for the source commit");
  workflowPublishState.textContent = published
    ? "Already on cgv-data/main — no new branch needed"
    : branchPrepared
      ? `Local branch ${state.publicationResult?.branch || payload.publisher?.branch} prepared`
      : exported
        ? "Ready to create a local publisher branch"
        : "Export this book first";
  workflowPublicationState.textContent = published
    ? "Present on cgv-data/main"
    : branchPrepared
      ? "Not published — push the branch and merge its PR"
      : "Prepare the publisher branch first";

  publicationHandoff.hidden = !branchPrepared || published;
  if (branchPrepared && !published) {
    publicationPushCommand.textContent = state.publicationResult?.pushCommand
      || payload.publisher?.pushCommand
      || "Use the push command printed by the publisher.";
    publicationPrLink.href = state.publicationResult?.pullRequestUrl || payload.publisher?.pullRequestUrl || "#";
    publicationCopyStatus.textContent = "";
  }

  verifyTranslationButton.disabled = state.workflowBusy || !["none", "draft"].includes(tr);
  approveTranslationButton.disabled = state.workflowBusy || tr !== "ready";
  continueAlignmentButton.disabled = state.workflowBusy || !translationDone || alignmentDone || alignmentRemaining === 0;
  continueAlignmentButton.textContent = alignmentRemaining
    ? `Continue alignment (${alignmentRemaining} phrases)`
    : "Alignment complete";
  verifyAlignmentButton.disabled = state.workflowBusy || !translationDone || alignmentRemaining !== 0 || !["none", "draft"].includes(al);
  approveAlignmentButton.disabled = state.workflowBusy || !translationDone || al !== "ready" || alignmentRemaining !== 0;
  reviewCommitButton.disabled = state.workflowBusy || state.commitBusy || !finished || committed || provenance.commitBlocked;
  reviewCommitButton.textContent = provenance.commitBlocked ? "Unstage other work first" : "Review changes";
  exportBookButton.disabled = state.workflowBusy || !finished || !committed || exported;
  exportBookButton.textContent = exported ? "Exported" : "Export book";
  publishBookButton.disabled = state.workflowBusy || state.publishBusy || !exported || branchPrepared || published;
  publishBookButton.textContent = published
    ? "Published"
    : branchPrepared
      ? "Branch prepared"
      : "Create publisher branch";

  const messages = {
    "verify-translation": "Translation work is saved. Run the canonical verifier.",
    "approve-translation": "Translation passed verification. Human approval is next.",
    align: `Review and confirm the ${alignmentRemaining} unfinished alignment phrases before verification.`,
    "verify-alignment": "Translation is approved. Finish the hand alignment, then verify it.",
    "approve-alignment": "Alignment passed verification. Human approval is next.",
    commit: "Both stages are approved. Review and commit this book before export.",
    export: "The book is finished. Export the validated package.",
    publish: "The package is current. Prepare its local publisher branch.",
    "publish-pr": "The branch is only local. Push it and merge its pull request before the book can reach the Reader.",
    complete: "This book's finished content is on cgv-data/main. Publication is complete."
  };
  workflowSummary.dataset.state = "ready";
  workflowSummary.textContent = messages[payload.workflow?.nextAction] || "Continue with the highlighted step.";
}

async function loadBookWorkflow() {
  try {
    const payload = await api(translationApiPath("/api/workflow"));
    renderBookWorkflow(payload);
    return payload;
  } catch (error) {
    workflowSummary.dataset.state = "error";
    workflowSummary.textContent = error.message || "Could not load canonical workflow status.";
    return null;
  }
}

async function runWorkflowAction(action, stage = "") {
  if (state.workflowBusy) return;
  if (isTranslationDirty()) await flushTranslationSave();
  state.workflowBusy = true;
  if (state.workflow) renderBookWorkflow(state.workflow);
  workflowSummary.textContent = action === "export" ? "Exporting…" : "Running canonical verification…";
  showWorkflowOutput("");
  let actionError = null;
  try {
    if (action === "export") state.publicationResult = null;
    const result = await api(translationApiPath("/api/workflow"), {
      method: "POST",
      body: JSON.stringify({ action, stage, book: state.bookId })
    });
    showWorkflowOutput(result.output || "Completed.");
    renderBookWorkflow(result.workflow || await loadBookWorkflow());
  } catch (error) {
    actionError = error;
    showWorkflowOutput(error.output || error.message || "Workflow action failed.");
    if (error.workflow) renderBookWorkflow(error.workflow);
    else await loadBookWorkflow();
    workflowSummary.dataset.state = "error";
    workflowSummary.textContent = error.message || "Workflow action failed.";
  } finally {
    state.workflowBusy = false;
    if (state.workflow) renderBookWorkflow(state.workflow);
    if (actionError) {
      workflowSummary.dataset.state = "error";
      workflowSummary.textContent = actionError.message || "Workflow action failed.";
    }
  }
}

function openWorkflowPublish() {
  if (!state.workflow?.export?.ready) return;
  workflowPublishDestination.value = state.workflow.publisher?.defaultDataRepo || "";
  workflowPublishConfirmation.checked = false;
  workflowPublishMessage.textContent = state.workflow.publisher?.destinationAvailable
    ? "This prepares a local branch only. The canonical publisher will validate the package before creating anything."
    : "The usual cgv-data checkout was not found. Select its existing checkout path.";
  workflowPublishModal.hidden = false;
  workflowPublishDestination.focus();
}

async function copyPublisherPushCommand() {
  const command = publicationPushCommand.textContent.trim();
  if (!command) return;
  try {
    await navigator.clipboard.writeText(command);
    publicationCopyStatus.textContent = "Push command copied.";
  } catch {
    publicationCopyStatus.textContent = "Could not copy automatically. Select and copy the command above.";
  }
}

function closeWorkflowPublish() {
  workflowPublishModal.hidden = true;
  workflowPublishMessage.textContent = "";
}

async function submitWorkflowPublish() {
  const dataRepo = workflowPublishDestination.value.trim();
  if (!dataRepo || !workflowPublishConfirmation.checked) {
    workflowPublishMessage.textContent = "Choose the cgv-data checkout and confirm creation of the local branch.";
    return;
  }
  state.publishBusy = true;
  confirmWorkflowPublish.disabled = true;
  cancelWorkflowPublish.disabled = true;
  workflowPublishMessage.textContent = "Validating the export and creating the local publisher branch…";
  try {
    const result = await api(translationApiPath("/api/workflow"), {
      method: "POST",
      body: JSON.stringify({
        action: "publish",
        dataRepo,
        humanConfirmation: true,
        book: state.bookId
      })
    });
    state.publicationResult = {
      ...(result.publication || {}),
      book: state.bookId,
      sourceCommit: result.workflow?.export?.sourceCommit || state.workflow?.export?.sourceCommit
    };
    closeWorkflowPublish();
    showWorkflowOutput(result.output || "Local publisher branch created.");
    renderBookWorkflow(result.workflow);
  } catch (error) {
    workflowPublishMessage.textContent = error.message || "The publisher branch was not created.";
    if (error.output) showWorkflowOutput(error.output);
    if (error.workflow) renderBookWorkflow(error.workflow);
  } finally {
    state.publishBusy = false;
    confirmWorkflowPublish.disabled = false;
    cancelWorkflowPublish.disabled = false;
    if (state.workflow) renderBookWorkflow(state.workflow);
  }
}

function openWorkflowApproval(stage) {
  state.approvalStage = stage;
  const label = stage === "translation" ? "translation" : "alignment";
  workflowApprovalTitle.textContent = `Approve ${label}`;
  workflowApprovalCopy.textContent = `Verification passed. This records your name and today's date in STATUS.md for this book's ${label}.`;
  workflowConfirmationCopy.textContent = `I personally reviewed the complete ${label} and approve it.`;
  workflowHumanConfirmation.checked = false;
  workflowApprovalMessage.textContent = "";
  workflowApprovalModal.hidden = false;
  workflowApproverName.focus();
}

function closeWorkflowApproval() {
  workflowApprovalModal.hidden = true;
  state.approvalStage = null;
  workflowApprovalMessage.textContent = "";
}

async function submitWorkflowApproval() {
  const approvedBy = workflowApproverName.value.trim();
  if (!approvedBy || !workflowHumanConfirmation.checked) {
    workflowApprovalMessage.textContent = "Enter your name and check the personal approval statement.";
    return;
  }
  confirmWorkflowApproval.disabled = true;
  try {
    const result = await api(translationApiPath("/api/workflow"), {
      method: "POST",
      body: JSON.stringify({
        action: "approve",
        stage: state.approvalStage,
        approvedBy,
        humanConfirmation: true,
        book: state.bookId
      })
    });
    closeWorkflowApproval();
    showWorkflowOutput(result.output || "Human approval recorded.");
    renderBookWorkflow(result.workflow);
  } catch (error) {
    workflowApprovalMessage.textContent = error.message || "Approval could not be recorded.";
    if (error.output) showWorkflowOutput(error.output);
  } finally {
    confirmWorkflowApproval.disabled = false;
  }
}

function openWorkflowCommit() {
  const provenance = state.workflow?.provenance;
  if (!provenance || provenance.committed) return;
  const changes = provenance.changes || [];
  workflowCommitFiles.textContent = changes.length
    ? changes.map(change => `${change.status || "  "}  ${change.path}`).join("\n")
    : "No selected-book changes found.";
  workflowCommitMessage.value = provenance.defaultMessage || `Finish ${state.workflow?.slug || state.bookId}`;
  workflowCommitConfirmation.checked = false;
  workflowCommitMessageText.textContent = provenance.commitBlocked
    ? `Commit blocked by already staged work: ${(provenance.stagedChanges || []).join(", ")}`
    : "Validation will run before the commit is created.";
  confirmWorkflowCommit.disabled = Boolean(provenance.commitBlocked);
  workflowCommitModal.hidden = false;
  workflowCommitMessage.focus();
}

function closeWorkflowCommit() {
  workflowCommitModal.hidden = true;
  workflowCommitMessageText.textContent = "";
}

async function submitWorkflowCommit() {
  const message = workflowCommitMessage.value.trim();
  if (!message || !workflowCommitConfirmation.checked) {
    workflowCommitMessageText.textContent = "Enter a commit message and confirm the exact file list.";
    return;
  }
  state.commitBusy = true;
  confirmWorkflowCommit.disabled = true;
  cancelWorkflowCommit.disabled = true;
  workflowCommitMessageText.textContent = "Validating and creating the selected-book commit…";
  try {
    const result = await api(translationApiPath("/api/workflow"), {
      method: "POST",
      body: JSON.stringify({
        action: "commit",
        message,
        humanConfirmation: true,
        book: state.bookId
      })
    });
    closeWorkflowCommit();
    showWorkflowOutput(result.output || "Selected-book commit created.");
    renderBookWorkflow(result.workflow);
  } catch (error) {
    workflowCommitMessageText.textContent = error.message || "The selected-book commit was not created.";
    if (error.output) showWorkflowOutput(error.output);
    if (error.workflow) renderBookWorkflow(error.workflow);
  } finally {
    state.commitBusy = false;
    confirmWorkflowCommit.disabled = false;
    cancelWorkflowCommit.disabled = false;
  }
}

function normalizeReferencePart(value = "") {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/gu, "")
    .replace(/\./gu, "")
    .replace(/\s+/gu, " ")
    .trim()
    .toLowerCase();
}

function activeBookLabel() {
  return bookSelect?.selectedOptions?.[0]?.textContent?.trim() || "";
}

function bookIdForReferenceLabel(label = "") {
  const normalized = normalizeReferencePart(label);
  if (!normalized || !bookSelect) return "";
  const prefixMatches = [];
  for (const option of bookSelect.options) {
    const optionLabel = normalizeReferencePart(option.textContent);
    const optionValue = normalizeReferencePart(option.value);
    if (normalized === optionLabel || normalized === optionValue) {
      return option.value;
    }
    if (optionLabel.startsWith(normalized) || optionValue.startsWith(normalized)) {
      prefixMatches.push(option.value);
    }
  }
  return prefixMatches.length === 1 ? prefixMatches[0] : "";
}

function parseReferenceJump(value = "") {
  const text = String(value || "").trim();
  const match = text.match(/^(?:(.+?)\s+)?(\d+)\s*[:.]\s*(\d+)$/u);
  if (!match) return null;

  const [, rawBookLabel, rawChapter, rawVerse] = match;
  const chapter = Number(rawChapter);
  const verse = Number(rawVerse);
  if (!Number.isInteger(chapter) || !Number.isInteger(verse) || chapter < 1 || verse < 1) {
    return null;
  }

  const bookLabel = (rawBookLabel || activeBookLabel()).trim();
  const bookId = rawBookLabel ? bookIdForReferenceLabel(bookLabel) : state.bookId;
  if (!bookId) return null;

  const resolvedLabel = rawBookLabel
    ? [...bookSelect.options].find(option => option.value === bookId)?.textContent?.trim() || bookLabel
    : activeBookLabel();

  return {
    bookId,
    reference: `${resolvedLabel} ${chapter}:${verse}`
  };
}

function findPhraseIndexByReference(reference) {
  const target = normalizeReferencePart(reference);
  return translationPhrases.findIndex(phrase => normalizeReferencePart(phrase.reference) === target);
}

async function switchTranslationBook(bookId) {
  state.bookId = bookId;
  if (bookSelect) bookSelect.value = bookId;
  const url = new URL(window.location.href);
  url.searchParams.set("book", state.bookId);
  window.history.replaceState(null, "", `${url.pathname}?${url.searchParams.toString()}`);
  state.phraseIndex = 0;
  state.translationLoadedFromDisk = false;
  translationUnitsLoaded = false;
  translationUnits = [];
  await loadInvestigations();
  await loadTranslationDocument();
  await loadBookWorkflow();
  await enrichPhraseReferencesFromUnits();
  await loadContinuationUnits({ force: true });
}

async function ensureReferenceLoaded(reference) {
  let index = findPhraseIndexByReference(reference);
  if (index !== -1) return index;

  let appended = true;
  while (appended) {
    appended = await appendNextTranslationUnit();
    index = findPhraseIndexByReference(reference);
    if (index !== -1) return index;
  }

  if (!translationUnitsLoaded) {
    await loadContinuationUnits({ force: true });
    index = findPhraseIndexByReference(reference);
    if (index !== -1) return index;
  }

  return -1;
}

async function jumpToReference(value = "") {
  const target = parseReferenceJump(value);
  if (!target) {
    referenceJumpStatus.textContent = "Use a reference like Daniel 1:1 or 1:1.";
    referenceJumpInput.focus();
    return;
  }

  referenceJumpStatus.textContent = "Loading...";
  try {
    await flushTranslationSave();
    if (target.bookId !== state.bookId) {
      await switchTranslationBook(target.bookId);
    }
    const index = await ensureReferenceLoaded(target.reference);
    if (index === -1) {
      referenceJumpStatus.textContent = `${target.reference} is not available.`;
      return;
    }

    state.phraseIndex = index;
    state.translationReturn = null;
    prototypeMessage.textContent = "";
    renderTranslationPhrase({ focus: true, cursorPosition: getPhraseEnd(index) });
    translationView.scrollTop = 0;
    referenceJumpInput.value = target.reference;
    referenceJumpStatus.textContent = "";
  } catch (error) {
    referenceJumpStatus.textContent = error.message || "Could not open reference.";
  }
}

async function loadAvailableBooks() {
  const { books = [], active } = await api("/api/translation/books").catch(() => ({ books: [], active: "titus" }));
  if (!bookSelect) return;
  const seeded = books.filter(book => book.hasPhrases);
  const options = seeded.length ? seeded : [{ id: "titus", label: "Titus", hasPhrases: true }];
  bookSelect.replaceChildren();
  for (const book of options) {
    const option = document.createElement("option");
    option.value = book.id;
    option.textContent = book.label;
    bookSelect.append(option);
  }
  if (!options.some(book => book.id === state.bookId)) {
    state.bookId = active || options[0].id;
  }
  bookSelect.value = state.bookId;
}

async function loadReverseLinks() {
  state.activeReverseUnitId = null;
  state.reverseLinksByPhrase = new Map();
  state.reverseLinksMeta = null;
  try {
    const doc = await api(translationApiPath("/api/translation/reverse-links"));
    const links = Array.isArray(doc?.links) ? doc.links : [];
    state.reverseLinksMeta = {
      textualBasis: doc?.textualBasis || "",
      stats: doc?.stats || {}
    };
    state.reverseLinksByPhrase = mapReverseLinksByTranslationPhrase(translationPhrases, links);
  } catch {
    state.reverseLinksByPhrase = new Map();
  }
}

function currentReverseLinkEntry() {
  return state.reverseLinksByPhrase.get(state.phraseIndex) || null;
}

function clearGreekLinkHighlights() {
  phraseInterlinear.querySelectorAll(".interlinear-token.is-linked").forEach(node => {
    node.classList.remove("is-linked");
  });
}

function highlightGreekTokenIds(tokenIds = []) {
  clearGreekLinkHighlights();
  const wanted = new Set((tokenIds || []).map(String));
  if (!wanted.size) return;
  phraseInterlinear.querySelectorAll(".interlinear-token[data-source-token-id]").forEach(node => {
    if (wanted.has(node.dataset.sourceTokenId)) {
      node.classList.add("is-linked");
    }
  });
}

function renderSpanishUnits() {
  if (!spanishUnits) return;
  spanishUnits.replaceChildren();
  const entry = currentReverseLinkEntry();
  const units = Array.isArray(entry?.units) ? entry.units : [];

  if (reverseLinksMeta) {
    if (!units.length) {
      reverseLinksMeta.hidden = false;
      reverseLinksMeta.textContent = state.bookId === "titus"
        ? "No reverse links for this phrase yet."
        : state.bookId === "daniel"
          ? "No reverse links for this phrase yet."
          : "Alignment has not started. Use Investigate under any source word above; no Spanish-word link is required.";
    } else {
      const status = entry?.status || "seeded";
      reverseLinksMeta.hidden = false;
      if (status === "seeded-hand") {
        reverseLinksMeta.textContent = "Seeded links — not human-confirmed. Review and confirm this entire phrase.";
      } else if (status === "gloss-seed") {
        reverseLinksMeta.textContent = "Gloss-seed links — click a Spanish unit to highlight Hebrew/Aramaic; hand-refine before trusting.";
      } else if (status === "seeded-ai") {
        reverseLinksMeta.textContent = "AI-seeded (lemma+morph) — click to highlight; confirm before trusting.";
      } else if (status === "seeded-ai-invalid" || status === "seeded-ai-error") {
        reverseLinksMeta.textContent = "AI seed needs repair — do not trust these links yet.";
      } else {
        reverseLinksMeta.textContent = "Auto-zip links — weak; prefer AI/hand review.";
      }
    }
  }

  if (!units.length) {
    const empty = document.createElement("span");
    empty.className = "reverse-links-meta";
    empty.textContent = "No Spanish-word alignment yet. Source-word investigations remain available above.";
    spanishUnits.append(empty);
    clearGreekLinkHighlights();
    return;
  }

  units.forEach(unit => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "spanish-unit";
    if (entry?.status === "seeded-auto" || entry?.status === "seeded-ai-invalid") {
      button.classList.add("is-auto");
    }
    if (state.activeReverseUnitId && state.activeReverseUnitId === unit.unitId) {
      button.classList.add("is-active");
    }
    button.dataset.unitId = unit.unitId || "";
    button.dataset.tokenIds = JSON.stringify(unit.sourceTokenIds || []);
    button.textContent = unit.surface || "—";
    button.title = (unit.sourceTokenIds || []).join(", ");
    spanishUnits.append(button);
  });

  if (state.activeReverseUnitId) {
    const active = units.find(unit => unit.unitId === state.activeReverseUnitId);
    if (active) highlightGreekTokenIds(active.sourceTokenIds);
    else {
      state.activeReverseUnitId = null;
      clearGreekLinkHighlights();
    }
  } else {
    clearGreekLinkHighlights();
  }
}

function closeAlignmentEditor() {
  document.body.classList.remove("alignment-editing");
  alignmentEditor.hidden = true;
  state.alignmentEditTokenIds = new Set();
  phraseInterlinear.querySelectorAll(".alignment-token-toggle").forEach(button => {
    button.setAttribute("aria-pressed", "false");
    button.textContent = "Link";
  });
}

function pendingAlignmentWork() {
  return pendingAlignmentWorkItems(state.reverseLinksByPhrase);
}

async function openNextAlignmentWork({ fromPhraseIndex = -1 } = {}) {
  if (state.workflow?.row?.translation !== "done") {
    workflowSummary.dataset.state = "error";
    workflowSummary.textContent = "Approve the translation before beginning alignment.";
    return false;
  }
  const pending = pendingAlignmentWork();
  if (!pending.length) {
    workflowSummary.dataset.state = "ready";
    workflowSummary.textContent = "All editable units are hand-aligned. Run Verify alignment.";
    return false;
  }
  const target = pending.find(item => item.phraseIndex >= fromPhraseIndex) || pending[0];
  const index = target.phraseIndex;
  if (index < 0) {
    workflowSummary.dataset.state = "error";
    workflowSummary.textContent = `Could not open alignment phrase ${target.phraseIndex}.`;
    return false;
  }
  state.phraseIndex = index;
  renderTranslationPhrase();
  state.activeReverseUnitId = String(target.unit.unitId || "");
  spanishUnits.querySelectorAll(".spanish-unit").forEach(node => {
    node.classList.toggle("is-active", node.dataset.unitId === state.activeReverseUnitId);
  });
  highlightGreekTokenIds(target.unit.sourceTokenIds || []);
  beginAlignmentEdit(target.unit);
  phraseInterlinear.scrollIntoView({ behavior: "smooth", block: "start" });
  const pendingPhrases = new Set(pending.map(item => item.phraseIndex)).size;
  setPhraseSaveStatus(`Review this phrase · ${pendingPhrases} phrases / ${pending.length} units remaining`, "dirty");
  return true;
}

function beginAlignmentEdit(unit) {
  if (state.workflow?.row?.translation !== "done") {
    workflowSummary.dataset.state = "error";
    workflowSummary.textContent = "The translation must be human-approved before alignment editing begins.";
    return;
  }
  state.activeReverseUnitId = String(unit.unitId || "");
  state.alignmentEditTokenIds = new Set((unit.sourceTokenIds || []).map(String));
  const pending = pendingAlignmentWork();
  const pendingPhrases = new Set(pending.map(item => item.phraseIndex)).size;
  alignmentReference.textContent = currentPhrase()?.reference || "Current phrase";
  alignmentProgress.textContent = `${pendingPhrases} phrases remaining`;
  alignmentSpanishContext.textContent = phraseDisplayText(currentPhrase()) || "—";
  alignmentUnitLabel.textContent = unit.surface || unit.unitId || "selected unit";
  reverseLinksMeta.hidden = false;
  reverseLinksMeta.textContent = "Select a Spanish unit to inspect its source link.";
  alignmentEditor.hidden = false;
  document.body.classList.add("alignment-editing");
  phraseInterlinear.querySelectorAll(".alignment-token-toggle").forEach(button => {
    const selected = state.alignmentEditTokenIds.has(button.dataset.sourceTokenId || "");
    button.setAttribute("aria-pressed", selected ? "true" : "false");
    button.textContent = selected ? "Linked" : "Link";
  });
}

function toggleAlignmentToken(button) {
  const tokenId = button.dataset.sourceTokenId || "";
  if (!tokenId) return;
  if (state.alignmentEditTokenIds.has(tokenId)) state.alignmentEditTokenIds.delete(tokenId);
  else state.alignmentEditTokenIds.add(tokenId);
  const selected = state.alignmentEditTokenIds.has(tokenId);
  button.setAttribute("aria-pressed", selected ? "true" : "false");
  button.textContent = selected ? "Linked" : "Link";
  highlightGreekTokenIds([...state.alignmentEditTokenIds]);
}

async function saveCurrentAlignmentEdit() {
  const entry = currentReverseLinkEntry();
  const unit = (entry?.units || []).find(item => String(item.unitId || "") === state.activeReverseUnitId);
  if (!entry || !unit) throw new Error("The selected alignment unit is no longer available.");
  if (!state.alignmentEditTokenIds.size) throw new Error("Select at least one source word.");
  const completedTranslationIndex = Number(entry._translationPhraseIndex);
  saveAlignmentEdit.disabled = true;
  try {
    await api(translationApiPath("/api/translation/reverse-links"), {
      method: "PUT",
      body: JSON.stringify({
        book: state.bookId,
        reference: entry.reference || currentPhrase().reference,
        phraseIndex: Number(entry.phraseIndex),
        unitId: unit.unitId,
        sourceTokenIds: [...state.alignmentEditTokenIds]
      })
    });
    closeAlignmentEditor();
    await loadReverseLinks();
    renderSpanishUnits();
    await loadBookWorkflow();
    setPhraseSaveStatus("Hand alignment saved", "saved");
    await openNextAlignmentWork({ fromPhraseIndex: completedTranslationIndex });
  } finally {
    saveAlignmentEdit.disabled = false;
  }
}

async function confirmCurrentAlignmentPhrase() {
  const entry = currentReverseLinkEntry();
  if (!entry) throw new Error("The current phrase has no alignment record.");
  const completedPhraseIndex = Number(entry.phraseIndex);
  const completedTranslationIndex = Number(entry._translationPhraseIndex);
  confirmAlignmentPhrase.disabled = true;
  try {
    await api(translationApiPath("/api/translation/reverse-links"), {
      method: "PUT",
      body: JSON.stringify({
        book: state.bookId,
        reference: entry.reference || currentPhrase().reference,
        phraseIndex: completedPhraseIndex,
        confirmPhrase: true
      })
    });
    closeAlignmentEditor();
    await loadReverseLinks();
    renderSpanishUnits();
    await loadBookWorkflow();
    setPhraseSaveStatus("Phrase hand-confirmed", "saved");
    await openNextAlignmentWork({ fromPhraseIndex: completedTranslationIndex + 1 });
  } finally {
    confirmAlignmentPhrase.disabled = false;
  }
}

async function loadTranslationDocument() {
  const { content, phrases, book, label } = await api(translationApiPath("/api/translation/current")).catch(() => ({ content: "", phrases: [] }));
  if (book) state.bookId = book;
  if (bookSelect && label) {
    const existing = [...bookSelect.options].some(option => option.value === state.bookId);
    if (!existing) {
      const option = document.createElement("option");
      option.value = state.bookId;
      option.textContent = label;
      bookSelect.append(option);
    }
    bookSelect.value = state.bookId;
  }
  if (Array.isArray(phrases) && phrases.length) {
    // When disk has a full phrase-level seed, trust that list order/content.
    // This keeps preliminary Spanish in the textarea instead of blank verse stubs.
    const sorted = [...phrases].sort(
      (a, b) => Number(a.phraseIndex || 0) - Number(b.phraseIndex || 0)
    );
    if (sorted.length >= defaultTranslationPhrases.length) {
      translationPhrases = sorted.map(record => makePhraseFromRecord(record));
      state.translationDirty = false;
      state.translationLoadedFromDisk = true;
      await loadReverseLinks();
      return;
    }

    const savedByKey = new Map(
      phrases.map(record => [phraseRecordKey(record), record])
    );

    const mergedCanonical = defaultTranslationPhrases.map((base, index) => {
      const saved = savedByKey.get(canonicalPhraseRecordKey(base, index));
      return mergeSavedRecord(base, saved, { preserveStructure: true });
    });

    const canonicalKeys = new Set(
      defaultTranslationPhrases.map((phrase, index) => canonicalPhraseRecordKey(phrase, index))
    );
    const extraPhrases = phrases
      .filter(record => !canonicalKeys.has(phraseRecordKey(record)))
      .sort((a, b) => Number(a.phraseIndex || 0) - Number(b.phraseIndex || 0))
      .map(record => mergeSavedRecord(makePhraseFromRecord(record), record));

    translationPhrases = [...mergedCanonical, ...extraPhrases];
    state.translationDirty = false;
    state.translationLoadedFromDisk = true;
    await loadReverseLinks();
    return;
  }

  resetTranslationPhrases();
  state.translationDirty = false;
  state.translationLoadedFromDisk = true;
  await loadReverseLinks();
}

function renderPhraseInterlinear() {
  phraseInterlinear.replaceChildren();
  const rows = currentPhrase().tokenRows || [];
  if (!rows.length) {
    const empty = document.createElement("p");
    empty.textContent = "—";
    phraseInterlinear.append(empty);
    return;
  }

  rows.forEach(token => {
    const item = document.createElement("div");
    item.className = "interlinear-token";
    if (token.sourceTokenId) {
      item.dataset.sourceTokenId = token.sourceTokenId;
    }

    const greekLine = document.createElement("div");
    greekLine.className = "interlinear-greek";
    const key = registerTokenAsGreekWord(token);
    if (key) {
      const info = greekWordInfo[key];
      const button = document.createElement("button");
      button.type = "button";
      button.className = `greek-word-trigger ${info.approved ? "approved" : "provisional"}`;
      button.dataset.greekKey = key;
      if (token.sourceTokenId) button.dataset.sourceTokenId = token.sourceTokenId;
      button.textContent = token.greek || token.surface || "—";
      button.title = "Open source-word investigation options";
      greekLine.append(button);
    } else {
      greekLine.textContent = token.greek || token.surface || "—";
    }

    const bleLine = document.createElement("div");
    bleLine.className = "interlinear-ble";
    bleLine.textContent = token.ble || token.es || token.strongs || "—";

    const rmacLine = document.createElement("div");
    rmacLine.className = "interlinear-rmac";
    rmacLine.textContent = token.rmac || token.morph || "—";

    const investigate = document.createElement("button");
    investigate.type = "button";
    investigate.className = "token-investigate-action";
    investigate.dataset.greekKey = key;
    if (token.sourceTokenId) investigate.dataset.sourceTokenId = token.sourceTokenId;
    investigate.textContent = "Investigate";
    investigate.setAttribute(
      "aria-label",
      `Investigate source word ${token.greek || token.surface || token.lemma || ""}`.trim()
    );

    const alignToggle = document.createElement("button");
    alignToggle.type = "button";
    alignToggle.className = "alignment-token-toggle";
    alignToggle.dataset.sourceTokenId = token.sourceTokenId || "";
    alignToggle.setAttribute("aria-pressed", state.alignmentEditTokenIds.has(String(token.sourceTokenId)) ? "true" : "false");
    alignToggle.textContent = state.alignmentEditTokenIds.has(String(token.sourceTokenId)) ? "Linked" : "Link";

    item.append(greekLine, bleLine, rmacLine, investigate, alignToggle);
    phraseInterlinear.append(item);
  });
}

function saveCurrentPhraseText() {
  syncTranslationDocumentFromEditor();
  renderVersePreview();
}

function renderVersePreview() {
  const reference = currentPhrase().reference || "Titus 1:1";
  const parts = translationPhrases
    .filter(phrase => phrase.reference === reference)
    .map(phrase => phraseDisplayText(phrase) || "[incomplete]");
  versePreviewText.textContent = parts.length ? parts.join(phraseSeparator) : "—";
}

function renderTranslationPhrase({ focus = false, cursorPosition = null } = {}) {
  closeAlignmentEditor();
  state.activeReverseUnitId = null;
  renderPhraseInterlinear();
  renderSpanishUnits();
  const phrase = currentPhrase();
  const reference = phrase.reference || "Titus 1:1";
  const phraseNumber = translationPhrases
    .filter(item => item.reference === reference)
    .findIndex(item => item === phrase) + 1;
  translationReferenceTitle.textContent = `${reference} · Phrase ${phraseNumber || state.phraseIndex + 1}`;
  translationReferenceMeta.textContent = reference;
  if (referenceJumpInput) {
    referenceJumpInput.placeholder = reference;
  }
  suggestionSourceLabel.textContent = suggestionSourceForPhrase(phrase);
  rv1909ReferenceText.textContent = phraseRv1909Text(phrase) || "—";
  bleReferenceText.textContent = phraseBleText(phrase) || "—";
  applyPipelineCache(phrase);
  if (translationEditor.value !== phrase.workingText) {
    translationEditor.value = phrase.workingText;
  }
  renderVersePreview();
  const dirty = (phrase.workingText || "") !== (phrase.savedText || "");
  state.translationDirty = dirty;
  setPhraseSaveStatus(dirty ? "Unsaved changes" : "Saved", dirty ? "dirty" : "saved");
  previousPhrase.disabled = state.phraseIndex === 0;
  nextPhrase.disabled = state.phraseIndex === translationPhrases.length - 1 && !hasMoreTranslationUnits();
  nextPhrase.textContent = nextPhrase.disabled ? "End of Available Text" : "Next Phrase";
  decisionPanel.hidden = true;

  if (focus) {
    const position = cursorPosition ?? translationEditor.value.length;
    placeTranslationCursor(position);
  }
}

function captureTranslationReturnPoint() {
  state.translationReturn = {
    phraseIndex: state.phraseIndex,
    scrollTop: translationView.scrollTop,
    selectionStart: translationEditor.selectionStart ?? getTranslationTargetEnd(),
    selectionEnd: translationEditor.selectionEnd ?? getTranslationTargetEnd()
  };
}

function placeTranslationCursor(position) {
  translationEditor.focus();
  translationEditor.setSelectionRange(position, position);
}

function showTranslationView({ focusTranslation = false, cursorPosition = null } = {}) {
  state.view = "translation";
  translationView.hidden = false;
  finalizationView.hidden = true;
  investigationView.hidden = true;
  sidebar.hidden = false;
  setInvestigationListOpen(false);
  const translationUrl = new URL(window.location.href);
  translationUrl.hash = "";
  translationUrl.searchParams.set("book", state.bookId);
  window.history.pushState(null, "", `${translationUrl.pathname}?${translationUrl.searchParams.toString()}`);
  if (state.translationReturn?.phraseIndex != null) {
    state.phraseIndex = state.translationReturn.phraseIndex;
    renderTranslationPhrase();
  }
  translationView.scrollTop = state.translationReturn?.scrollTop || 0;
  if (focusTranslation) {
    placeTranslationCursor(cursorPosition ?? state.translationReturn?.selectionEnd ?? getTranslationTargetEnd());
    requestAnimationFrame(() => {
      translationView.scrollTop = state.translationReturn?.scrollTop || 0;
    });
  } else {
    translationEditor.focus();
  }
}

function showInvestigationView() {
  state.view = "investigation";
  translationView.hidden = true;
  finalizationView.hidden = true;
  investigationView.hidden = false;
  sidebar.hidden = false;
  window.location.hash = `investigation/${state.investigation}`;
}

async function showFinalizationView() {
  if (state.view === "translation") {
    saveCurrentPhraseText();
    captureTranslationReturnPoint();
    await flushTranslationSave();
  }
  state.view = "finalization";
  translationView.hidden = true;
  investigationView.hidden = true;
  finalizationView.hidden = false;
  sidebar.hidden = true;
  setInvestigationListOpen(false);
  finalizationBookTitle.textContent = state.workflow?.label || activeBookLabel() || "this book";
  finalizationView.scrollTop = 0;
  await loadBookWorkflow();
}

function setStatus(text, stateName = "saved") {
  saveStatus.textContent = text;
  saveStatus.dataset.state = stateName;
}

function positionDecisionPanel(anchor) {
  const anchorRect = anchor.getBoundingClientRect();
  const panelRect = decisionPanel.getBoundingClientRect();
  const margin = 12;
  const viewportPadding = 12;
  let left = anchorRect.left + (anchorRect.width / 2) - (panelRect.width / 2);
  let top = anchorRect.bottom + margin;

  left = Math.max(viewportPadding, Math.min(left, window.innerWidth - panelRect.width - viewportPadding));

  if (top + panelRect.height + viewportPadding > window.innerHeight) {
    top = anchorRect.top - panelRect.height - margin;
  }

  top = Math.max(viewportPadding, top);
  decisionPanel.style.left = `${left}px`;
  decisionPanel.style.top = `${top}px`;
}

function hideGreekDecisionPanel() {
  decisionPanel.hidden = true;
}

function showGreekDecisionPanel(key, anchor) {
  const info = greekWordInfo[key];
  if (!info) return;

  state.selectedGreekKey = key;
  decisionPanel.hidden = false;
  decisionPanelLemma.textContent = [info.strongs, info.lemma].filter(Boolean).join(" — ") || info.lemma || "—";
  decisionPanelPolicy.textContent = info.approved
    ? info.rendering
    : `${info.rendering || "—"} (${info.source || "unresolved"})`;
  if (decisionPanelSpanish) {
    decisionPanelSpanish.textContent = phraseDisplayText(currentPhrase()) || "—";
  }
  if (info.investigationId) {
    decisionPanelStatus.textContent = info.approved
      ? `Approved · ${info.investigationId}`
      : `Open · ${info.investigationId}`;
    openInvestigationButton.textContent = info.approved ? "View Decision" : "Open Investigation";
  } else {
    decisionPanelStatus.textContent = "No investigation yet";
    openInvestigationButton.textContent = "Start Investigation";
  }
  positionDecisionPanel(anchor);
}

function decisionHasHumanApproval(decision) {
  return decision?.status === "Approved"
    && decision?.approvalAuthority === "human"
    && Boolean(String(decision?.approvedBy || "").trim())
    && Boolean(String(decision?.approvedAt || "").trim());
}

function applyDecisionToTranslation(decision) {
  if (!decisionHasHumanApproval(decision) || !decision.preferredRendering) return;

  const greekKey = greekKeyByStrong[decision.strongs]
    || linkInvestigationToWordInfo({
      lemma: decision.lemma,
      strongs: decision.strongs,
      investigationId: decision.investigationId || "",
      approved: true,
      rendering: decision.preferredRendering,
      source: `Decision ${decision.version}`
    });
  const alreadyApplied = greekKey
    && greekWordInfo[greekKey]?.approved
    && greekWordInfo[greekKey]?.source === `Decision ${decision.version}`;
  if (greekKey && greekWordInfo[greekKey]) {
    greekWordInfo[greekKey] = {
      ...greekWordInfo[greekKey],
      approved: true,
      rendering: decision.preferredRendering,
      source: `Decision ${decision.version}`
    };
  }

  const decisionPhrase = translationPhrases.find(phrase => phrase.decisionStrong === decision.strongs);
  if (decisionPhrase && !alreadyApplied) {
    decisionPhrase.approvedDecision = true;
  }
}

async function loadApprovedDecisions({ applyToText = !state.translationLoadedFromDisk } = {}) {
  const { investigations } = await api(translationApiPath("/api/investigations"));
  const decisions = [];

  for (const id of investigations) {
    const { decision } = await api(`/api/investigations/${id}/decision`).catch(() => ({ decision: null }));
    if (!decision) continue;

    linkInvestigationToWordInfo({
      lemma: decision.lemma,
      strongs: decision.strongs,
      investigationId: id,
      approved: decisionHasHumanApproval(decision) && Boolean(decision.preferredRendering),
      rendering: decision.preferredRendering || "",
      source: decisionHasHumanApproval(decision)
        ? `Human-approved decision ${decision.version}`
        : decision.status === "Approved"
          ? "Approved status missing human provenance"
          : decision.status || "Draft"
    });

    if (decisionHasHumanApproval(decision) && decision.preferredRendering) {
      decisions.push({ ...decision, investigationId: id });
      if (applyToText) {
        applyDecisionToTranslation({ ...decision, investigationId: id });
      }
    }
  }

  renderTranslationPhrase();
  return decisions.find(decision => decision.strongs === currentPhrase().decisionStrong) || null;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const error = new Error(body.error || `Request failed: ${response.status}`);
    error.code = body.code;
    error.status = response.status;
    error.fileName = body.fileName;
    error.output = body.output;
    error.workflow = body.workflow;
    throw error;
  }
  return response.json();
}

async function fetchText(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.text();
}

async function loadInvestigations() {
  const { investigations } = await api(translationApiPath("/api/investigations"));
  investigationList.innerHTML = "";
  sourceInvestigationByOshbId.clear();

  await Promise.all(investigations.map(async id => {
    try {
      const content = await fetchText(`/api/investigations/${id}/evidence/source-variants.json`);
      const evidence = JSON.parse(content);
      if (evidence.recordType !== "SOURCE_VARIANT_EVIDENCE"
        || evidence.book !== state.bookId
        || !Array.isArray(evidence.variants)) {
        return;
      }
      for (const variant of evidence.variants) {
        for (const reading of [variant.ketiv, variant.qere]) {
          const oshbId = String(reading?.id || "").trim();
          if (oshbId) sourceInvestigationByOshbId.set(oshbId, id);
        }
      }
    } catch {
      // Most investigations do not contain source-variant evidence.
    }
  }));

  for (const id of investigations) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `investigation-item${id === state.investigation ? " active" : ""}`;
    button.textContent = id;
    button.addEventListener("click", () => openInvestigation(id));
    investigationList.append(button);
  }
}

function setInvestigationListOpen(open) {
  document.body.classList.toggle("investigations-open", open);
  investigationToggle.setAttribute("aria-expanded", String(open));
}

function renderTabs() {
  tabBar.innerHTML = "";
  for (const tab of tabs) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `tab${tab.file === state.tab.file ? " active" : ""}`;
    button.textContent = tab.id;
    button.addEventListener("click", () => openTab(tab));
    tabBar.append(button);
  }
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderInlineMarkdown(value) {
  const escaped = escapeHtml(value);
  return escaped.replace(/\*\*([^*]+)\*\*/gu, "<mark class=\"witness-focus\">$1</mark>");
}

function appendMarkdownParagraph(parent, line) {
  const fieldMatch = line.match(/^([^:]+):\s*(.*)$/u);
  const paragraph = document.createElement("p");

  if (fieldMatch) {
    paragraph.className = "evidence-line";
    const label = document.createElement("strong");
    label.textContent = `${fieldMatch[1]}:`;
    paragraph.append(label, " ");
    const value = document.createElement("span");
    value.innerHTML = renderInlineMarkdown(fieldMatch[2]);
    paragraph.append(value);
  } else {
    paragraph.innerHTML = renderInlineMarkdown(line);
  }

  parent.append(paragraph);
}

function splitMarkdownTableRow(line) {
  const cells = line.trim().split("|");
  if (cells[0] === "") cells.shift();
  if (cells[cells.length - 1] === "") cells.pop();
  return cells.map(cell => cell.trim());
}

function isMarkdownTableSeparator(line) {
  return splitMarkdownTableRow(line).every(cell => /^:?-{3,}:?$/u.test(cell));
}

function appendMarkdownTable(parent, lines) {
  const [headerLine, , ...bodyLines] = lines;
  const table = document.createElement("table");
  const thead = document.createElement("thead");
  const tbody = document.createElement("tbody");
  const headerRow = document.createElement("tr");

  for (const cell of splitMarkdownTableRow(headerLine)) {
    const th = document.createElement("th");
    th.innerHTML = renderInlineMarkdown(cell);
    headerRow.append(th);
  }
  thead.append(headerRow);

  for (const line of bodyLines) {
    const row = document.createElement("tr");
    for (const cell of splitMarkdownTableRow(line)) {
      const td = document.createElement("td");
      td.innerHTML = renderInlineMarkdown(cell);
      row.append(td);
    }
    tbody.append(row);
  }

  table.append(thead, tbody);
  parent.append(table);
}

function renderEvidenceMarkdown(markdown) {
  const fragment = document.createDocumentFragment();
  const stack = [fragment];
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");

  const currentParent = () => stack[stack.length - 1];

  for (let index = 0; index < lines.length; index += 1) {
    const rawLine = lines[index];
    const line = rawLine.trim();
    if (!line) continue;

    if (
      line.startsWith("|")
      && lines[index + 1]?.trim().startsWith("|")
      && isMarkdownTableSeparator(lines[index + 1])
    ) {
      const tableLines = [line, lines[index + 1].trim()];
      index += 2;
      while (index < lines.length && lines[index].trim().startsWith("|")) {
        tableLines.push(lines[index].trim());
        index += 1;
      }
      index -= 1;
      appendMarkdownTable(currentParent(), tableLines);
      continue;
    }

    if (line === "<details>") {
      const details = document.createElement("details");
      details.className = "usage-block";
      currentParent().append(details);
      stack.push(details);
      continue;
    }

    if (line === "</details>") {
      if (stack.length > 1) stack.pop();
      continue;
    }

    const summaryMatch = line.match(/^<summary>(.*)<\/summary>$/u);
    if (summaryMatch) {
      const summary = document.createElement("summary");
      summary.textContent = summaryMatch[1];
      currentParent().append(summary);
      continue;
    }

    const headingMatch = line.match(/^(#{1,6})\s+(.+)$/u);
    if (headingMatch) {
      const level = Math.min(headingMatch[1].length, 4);
      const heading = document.createElement(`h${level}`);
      heading.textContent = headingMatch[2];
      currentParent().append(heading);
      continue;
    }

    if (line === "---") {
      currentParent().append(document.createElement("hr"));
      continue;
    }

    appendMarkdownParagraph(currentParent(), line.replace(/\s{2}$/u, ""));
  }

  evidenceViewer.replaceChildren(fragment);
}

function showEditor() {
  editor.hidden = false;
  evidenceViewer.hidden = true;
  decisionEditor.hidden = true;
}

function showEvidenceViewer() {
  editor.hidden = true;
  evidenceViewer.hidden = false;
  decisionEditor.hidden = true;
}

function showDecisionEditor() {
  editor.hidden = true;
  evidenceViewer.hidden = true;
  decisionEditor.hidden = false;
}

function fillDecisionForm(decision) {
  state.decision = decision;
  decisionStatus.value = decision.status || "Draft";
  decisionVersion.value = decision.version || "1.0";
  decisionEffectiveDate.value = decision.effectiveDate || "";
  decisionLemma.value = decision.lemma || "";
  decisionStrongs.value = decision.strongs || "";
  decisionRendering.value = decision.preferredRendering || "";
  decisionConfidence.value = decision.confidence || "Medium";
  decisionReason.value = decision.reason || "";
  decisionScope.value = decision.scope || "";
  decisionScopeReference.value = decision.scopeReference || "";
  decisionScopeCondition.value = decision.scopeCondition || "";
  decisionApprovalAuthority.value = decision.approvalAuthority || "";
  decisionApprovedBy.value = decision.approvedBy || "";
  decisionApprovedAt.value = decision.approvedAt || "";
  const humanApproved = decisionHasHumanApproval(decision);
  approveDecision.disabled = humanApproved || decision.status === "Superseded";
  approveDecision.textContent = decision.status === "Approved" && !humanApproved
    ? "Record Human Approval"
    : "Approve";
  decisionStatus.disabled = decision.status === "Approved" || decision.status === "Superseded";
}

function readDecisionForm() {
  return {
    status: decisionStatus.value,
    effectiveDate: decisionEffectiveDate.value,
    preferredRendering: decisionRendering.value,
    confidence: decisionConfidence.value,
    scope: decisionScope.value,
    scopeReference: decisionScopeReference.value,
    scopeCondition: decisionScopeCondition.value,
    reason: decisionReason.value
  };
}

async function saveDecision(action = "save", approval = {}) {
  const { decision } = await api(`/api/investigations/${state.investigation}/decision`, {
    method: "PUT",
    body: JSON.stringify({ ...readDecisionForm(), ...approval, action })
  });
  fillDecisionForm(decision);
  state.dirty = false;
  setStatus(action === "approve" ? "Approved" : "Saved", "saved");
  await loadInvestigationMeta();
  await loadApprovedDecisions({ applyToText: action === "approve" });
  scheduleTranslationSave();
}

async function returnToTranslation() {
  await saveCurrent();
  const decision = await loadApprovedDecisions({ applyToText: true });
  await saveTranslationDocument();
  const approvedRendering = decisionHasHumanApproval(decision) ? decision.preferredRendering : "";
  const cursorPosition = approvedRendering
    ? getTranslationTargetEnd(approvedRendering)
    : state.translationReturn?.selectionEnd ?? getTranslationTargetEnd();
  showTranslationView({ focusTranslation: true, cursorPosition });
}

async function movePhrase(direction) {
  try {
    await flushTranslationSave();
  } catch (error) {
    setPhraseSaveStatus("Save error", "error");
    prototypeMessage.textContent = error.message || "Translation save error.";
    return;
  }
  let nextIndex = state.phraseIndex + direction;
  if (direction > 0 && nextIndex >= translationPhrases.length) {
    let appended = await appendNextTranslationUnit();
    if (!appended) {
      await loadContinuationUnits({ force: true });
      appended = await appendNextTranslationUnit();
    }
    if (!appended) {
      renderTranslationPhrase();
      prototypeMessage.textContent = hasMoreTranslationUnits()
        ? "Could not load the next verse."
        : "End of available Titus text.";
      return;
    }
    nextIndex = state.phraseIndex + direction;
  }
  if (nextIndex < 0 || nextIndex >= translationPhrases.length) return;
  state.phraseIndex = nextIndex;
  state.translationReturn = {
    phraseIndex: state.phraseIndex,
    scrollTop: translationView.scrollTop,
    selectionStart: 0,
    selectionEnd: 0
  };
  prototypeMessage.textContent = "";
  renderTranslationPhrase();
  translationEditor.focus();
  placeTranslationCursor(getPhraseEnd());
}

async function saveCurrent() {
  if (state.evidenceFile || !state.dirty || state.saving) return;
  state.saving = true;
  saveButton.disabled = true;
  setStatus("Saving...", "saving");

  try {
    if (state.tab.file === "decision.md") {
      await saveDecision();
    } else {
      await api(`/api/investigations/${state.investigation}/files/${encodeURIComponent(state.tab.file)}`, {
        method: "PUT",
        body: JSON.stringify({ content: editor.value })
      });
      state.dirty = false;
      setStatus("Saved", "saved");
    }
  } catch (error) {
    setStatus("Save error", "error");
    throw error;
  } finally {
    state.saving = false;
    saveButton.disabled = false;
  }
}

async function loadInvestigationMeta() {
  const { meta } = await api(`/api/investigations/${state.investigation}`);
  metaPrimarySubject.textContent = meta.primarySubject || "-";
  metaOriginReference.textContent = meta.originReference || "-";
  metaCurrentStatus.textContent = meta.currentStatus || "-";
}

async function openInvestigation(id) {
  if (state.view === "translation") {
    saveCurrentPhraseText();
    captureTranslationReturnPoint();
    await flushTranslationSave();
  }
  await saveCurrent();
  state.investigation = id;
  state.tab = tabs[0];
  state.evidenceFile = null;
  showInvestigationView();
  title.textContent = id;
  await loadInvestigations();
  setInvestigationListOpen(false);
  await loadInvestigationMeta();
  renderTabs();
  await loadCurrentFile();
}

async function openTab(tab) {
  if (!state.evidenceFile && tab.file === state.tab.file) return;
  await saveCurrent();
  state.tab = tab;
  state.evidenceFile = null;
  renderTabs();
  await loadCurrentFile();
}

async function loadCurrentFile() {
  if (state.tab.file === "decision.md") {
    showDecisionEditor();
    saveButton.disabled = false;
    setStatus("Loading...", "saving");
    prototypeMessage.textContent = "";
    const { decision } = await api(`/api/investigations/${state.investigation}/decision`);
    fillDecisionForm(decision);
    state.dirty = false;
    setStatus("Saved", "saved");
    decisionRendering.focus();
    await renderEvidenceFiles();
    return;
  }

  showEditor();
  editor.disabled = true;
  editor.readOnly = false;
  saveButton.disabled = false;
  setStatus("Loading...", "saving");
  prototypeMessage.textContent = "";
  const { content } = await api(
    `/api/investigations/${state.investigation}/files/${encodeURIComponent(state.tab.file)}`
  );
  editor.value = content;
  state.dirty = false;
  editor.disabled = false;
  editor.focus();
  setStatus("Saved", "saved");
  await renderEvidenceFiles();
}

async function openEvidenceFile(fileName) {
  await saveCurrent();
  editor.disabled = true;
  editor.readOnly = true;
  saveButton.disabled = true;
  setStatus("Evidence file", "saved");
  prototypeMessage.textContent = "";

  const content = await fetchText(
    `/api/investigations/${state.investigation}/evidence/${encodeURIComponent(fileName)}`
  );
  state.evidenceFile = fileName;
  editor.value = content;
  renderEvidenceMarkdown(content);
  state.dirty = false;
  showEvidenceViewer();
  editor.disabled = false;
  evidenceViewer.focus();
  prototypeMessage.textContent = `Viewing ${fileName}.`;
}

async function renderEvidenceFiles() {
  if (state.tab.file !== "evidence.md") {
    evidenceFiles.hidden = true;
    evidenceFiles.innerHTML = "";
    return;
  }

  const { files } = await api(`/api/investigations/${state.investigation}/evidence`);
  evidenceFiles.innerHTML = "";

  if (!files.length) {
    evidenceFiles.hidden = true;
    return;
  }

  const heading = document.createElement("p");
  heading.className = "evidence-files-label";
  heading.textContent = "Available evidence";
  evidenceFiles.append(heading);

  const list = document.createElement("div");
  list.className = "evidence-file-list";

  for (const file of files) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "evidence-file-card";
    button.textContent = file.name;
    button.addEventListener("click", () => {
      void openEvidenceFile(file.name).catch(error => {
        prototypeMessage.textContent = error.message || "Evidence file error.";
      });
    });
    list.append(button);
  }

  evidenceFiles.append(list);
  evidenceFiles.hidden = false;
}

async function syncGatherSubjectFromInvestigation() {
  const { decision } = await api(`/api/investigations/${state.investigation}/decision`).catch(() => ({ decision: null }));
  const meta = await api(`/api/investigations/${state.investigation}`).then(payload => payload.meta).catch(() => null);
  const primary = String(meta?.primarySubject || "");
  const primaryStrongs = (primary.match(/\b[GHA]\d+\b/i) || [])[0] || "";
  const primaryLemma = primary.replace(/^[GHA]\d+\s*[—-]\s*/iu, "").trim();

  const lemma = decision?.lemma || primaryLemma || decisionLemma?.value || "";
  const strongs = decision?.strongs || primaryStrongs || decisionStrongs?.value || "";
  const key = linkInvestigationToWordInfo({
    lemma,
    strongs,
    investigationId: state.investigation,
    approved: decisionHasHumanApproval(decision),
    rendering: decision?.preferredRendering || "",
    source: decision?.status || "Investigation"
  });

  if (key) {
    state.selectedGreekKey = key;
    greekWordInfo[key] = {
      ...greekWordInfo[key],
      language: sourceLanguageForToken({ strongs, lemma, surface: greekWordInfo[key].surface }),
      reference: meta?.originReference || greekWordInfo[key].reference || "Titus 1:1",
      surface: greekWordInfo[key].surface || lemma
    };
  }

  return greekWordInfo[key] || selectedGreekInfo();
}

async function openGatherModal() {
  try {
    await syncGatherSubjectFromInvestigation();
  } catch (error) {
    gatherMessage.textContent = error.message || "Could not load investigation subject.";
  }

  const info = selectedGreekInfo();
  const constructionInput = document.querySelector("input[name='gather-type'][value='construction']");
  const hebrewSubject = sourceLanguageForToken(info) === "hebrew";
  if (constructionInput) {
    constructionInput.disabled = !info.construction || hebrewSubject;
    if (constructionInput.disabled && constructionInput.checked) {
      document.querySelector("input[name='gather-type'][value='occurrences']").checked = true;
    }
  }
  gatherMessage.textContent = info.lemma || info.strongs
    ? `Subject: ${[info.strongs, info.lemma].filter(Boolean).join(" — ")}${hebrewSubject ? " (OT / OSHB)" : ""}`
    : "Set lemma/Strong's in Decision before gathering.";
  replaceActions.hidden = true;
  runGather.disabled = !(info.lemma || info.strongs);
  gatherModal.hidden = false;
  runGather.focus();
}

function closeGatherModal() {
  gatherModal.hidden = true;
  gatherMessage.textContent = "";
  replaceActions.hidden = true;
}

function buildGatherPayload(type, replace) {
  const info = selectedGreekInfo();
  return {
    type,
    replace,
    reference: info.reference || metaOriginReference?.textContent || "Titus 1:1",
    surface: info.surface || "",
    lemma: info.lemma || decisionLemma?.value?.trim() || "",
    strongs: info.strongs || decisionStrongs?.value?.trim() || "",
    rmac: info.rmac || "",
    prepositionSurface: info.construction?.prepositionSurface || "",
    prepositionLemma: info.construction?.prepositionLemma || "",
    caseCode: info.construction?.caseCode || ""
  };
}

function selectedGatherType() {
  return document.querySelector("input[name='gather-type']:checked")?.value || "occurrences";
}

async function runEvidenceGather({ replace = false } = {}) {
  const type = selectedGatherType();
  const labels = {
    occurrence: "occurrence",
    occurrences: "lemma",
    construction: "construction"
  };
  gatherMessage.textContent = replace
    ? `Replacing ${labels[type] || "evidence"} evidence...`
    : `Gathering ${labels[type] || "evidence"} evidence...`;
  runGather.disabled = true;
  replaceEvidence.disabled = true;

  try {
    await syncGatherSubjectFromInvestigation();
    const result = await api(`/api/investigations/${state.investigation}/gather`, {
      method: "POST",
      body: JSON.stringify(buildGatherPayload(type, replace))
    });
    prototypeMessage.textContent = "Evidence gathered.";
    closeGatherModal();
    const evidenceTab = tabs.find(tab => tab.file === "evidence.md") || tabs[0];
    state.tab = evidenceTab;
    renderTabs();
    await renderEvidenceFiles();
    if (result?.file?.name) {
      await openEvidenceFile(result.file.name);
    } else if (state.tab.file === "history.md") {
      await loadCurrentFile();
    }
  } catch (error) {
    if (error.code === "EVIDENCE_EXISTS") {
      gatherMessage.textContent = "";
      replaceMessage.textContent = `${error.fileName || "Evidence"} already exists.`;
      replaceActions.hidden = false;
      replaceEvidence.disabled = false;
      replaceEvidence.focus();
      return;
    }
    gatherMessage.textContent = error.message || "Gather error.";
  } finally {
    runGather.disabled = false;
    replaceEvidence.disabled = false;
  }
}

editor.addEventListener("input", () => {
  if (state.evidenceFile) return;
  state.dirty = true;
  setStatus("Unsaved changes", "dirty");
});

translationEditor.addEventListener("input", () => {
  syncTranslationDocumentFromEditor();
  renderVersePreview();
  markTranslationDirty();
});

[
  decisionStatus,
  decisionEffectiveDate,
  decisionRendering,
  decisionConfidence,
  decisionScope,
  decisionScopeReference,
  decisionScopeCondition,
  decisionReason
].forEach(control => {
  control.addEventListener("input", () => {
    state.dirty = true;
    setStatus("Unsaved changes", "dirty");
  });
});

saveButton.addEventListener("click", () => {
  void saveCurrent().catch(() => {});
});

approveDecision.addEventListener("click", () => {
  void (async () => {
    const scope = decisionScope.value;
    if (!scope) {
      prototypeMessage.textContent = "Select the decision scope before approval.";
      decisionScope.focus();
      return;
    }
    if (scope === "Occurrence" && !decisionScopeReference.value.trim()) {
      prototypeMessage.textContent = "Occurrence scope requires a reference.";
      decisionScopeReference.focus();
      return;
    }
    if (scope === "Construction" && !decisionScopeCondition.value.trim()) {
      prototypeMessage.textContent = "Construction scope requires a condition.";
      decisionScopeCondition.focus();
      return;
    }
    const approver = window.prompt(
      `Type the human approver's name. This approves the rendering and its ${scope} scope.`
    );
    if (approver == null) return;
    const approvedBy = approver.trim();
    if (!approvedBy) {
      prototypeMessage.textContent = "Human approver name is required.";
      return;
    }
    await saveDecision("approve", { approvedBy, humanConfirmation: true });
    prototypeMessage.textContent = "Human approval recorded.";
  })().catch(error => {
    prototypeMessage.textContent = error.message || "Decision approval error.";
  });
});

phraseInterlinear.addEventListener("click", event => {
  if (event.target instanceof HTMLElement && event.target.classList.contains("alignment-token-toggle")) {
    event.stopPropagation();
    toggleAlignmentToken(event.target);
    return;
  }
  if (event.target instanceof HTMLElement && event.target.dataset.greekKey) {
    event.stopPropagation();
    showGreekDecisionPanel(event.target.dataset.greekKey, event.target);
  }
});

spanishUnits?.addEventListener("click", event => {
  const target = event.target;
  if (!(target instanceof HTMLElement) || !target.classList.contains("spanish-unit")) return;
  event.stopPropagation();
  const unitId = target.dataset.unitId || "";
  let tokenIds = [];
  try {
    tokenIds = JSON.parse(target.dataset.tokenIds || "[]");
  } catch {
    tokenIds = [];
  }
  if (state.activeReverseUnitId === unitId) {
    state.activeReverseUnitId = null;
    closeAlignmentEditor();
    clearGreekLinkHighlights();
    spanishUnits.querySelectorAll(".spanish-unit.is-active").forEach(node => node.classList.remove("is-active"));
    return;
  }
  state.activeReverseUnitId = unitId;
  spanishUnits.querySelectorAll(".spanish-unit").forEach(node => {
    node.classList.toggle("is-active", node.dataset.unitId === unitId);
  });
  highlightGreekTokenIds(tokenIds);
  const unit = (currentReverseLinkEntry()?.units || []).find(item => String(item.unitId || "") === unitId);
  if (unit) beginAlignmentEdit(unit);
});

function isHebrewStrongs(strongs = "") {
  return /^[HA]\d+/i.test(String(strongs || "").trim());
}

function sourceLanguageForToken(info = {}) {
  if (info.language) return info.language;
  if (isHebrewStrongs(info.strongs)) return "hebrew";
  if (/[\u0590-\u05FF]/u.test(info.surface || info.lemma || "")) return "hebrew";
  return "greek";
}

async function createInvestigationFromLemma(payload = {}) {
  const lemma = String(payload.lemma || "").trim();
  if (!lemma) {
    throw new Error("Lemma is required to start an investigation.");
  }

  const language = payload.language || sourceLanguageForToken(payload);
  const result = await api(translationApiPath("/api/investigations"), {
    method: "POST",
    body: JSON.stringify({
      lemma,
      strongs: payload.strongs || "",
      language,
      reference: payload.reference || currentPhrase()?.reference || "Titus 1:1",
      clause: payload.clause || phraseGreekText(currentPhrase()),
      surface: payload.surface || "",
      ble: payload.ble || payload.rendering || "",
      book: payload.book || state.bookId || ""
    })
  });

  const key = linkInvestigationToWordInfo({
    lemma: result.lemma || lemma,
    strongs: result.strongs || payload.strongs || "",
    investigationId: result.id,
    approved: false,
    rendering: payload.ble || payload.rendering || "",
    source: result.existing ? "Existing investigation" : "New investigation"
  });
  if (key) {
    state.selectedGreekKey = key;
    if (greekWordInfo[key]) {
      greekWordInfo[key].language = result.language || language;
    }
  }

  await loadInvestigations();
  hideGreekDecisionPanel();
  await openInvestigation(result.id);
  prototypeMessage.textContent = result.created
    ? `Created ${result.id} for ${result.lemma || lemma}.`
    : `Opened existing ${result.id} for ${result.lemma || lemma}.`;
  return result;
}

function openNewInvestigationModal(seed = {}) {
  if (!newInvestigationModal) return;
  const info = greekWordInfo[state.selectedGreekKey];
  newInvLemma.value = seed.lemma || info?.lemma || "";
  newInvStrongs.value = seed.strongs || info?.strongs || "";
  newInvReference.value = seed.reference || info?.reference || currentPhrase()?.reference || "Titus 1:1";
  newInvestigationMessage.textContent = "";
  newInvestigationModal.hidden = false;
  newInvLemma.focus();
  newInvLemma.select();
}

function closeNewInvestigationModal() {
  if (!newInvestigationModal) return;
  newInvestigationModal.hidden = true;
  newInvestigationMessage.textContent = "";
}

async function submitNewInvestigationModal() {
  const lemma = newInvLemma.value.trim();
  if (!lemma) {
    newInvestigationMessage.textContent = "Lemma is required.";
    newInvLemma.focus();
    return;
  }
  createNewInvestigationButton.disabled = true;
  try {
    await createInvestigationFromLemma({
      lemma,
      strongs: newInvStrongs.value.trim(),
      language: sourceLanguageForToken({
        lemma,
        strongs: newInvStrongs.value.trim(),
        surface: lemma
      }),
      reference: newInvReference.value.trim() || currentPhrase()?.reference || "Titus 1:1",
      clause: phraseGreekText(currentPhrase()),
      surface: lemma,
      ble: ""
    });
    closeNewInvestigationModal();
  } finally {
    createNewInvestigationButton.disabled = false;
  }
}

openInvestigationButton.addEventListener("click", () => {
  const info = greekWordInfo[state.selectedGreekKey];
  if (!info) {
    prototypeMessage.textContent = "Select a source word first.";
    return;
  }
  if (info.investigationId) {
    void openInvestigation(info.investigationId);
    return;
  }
  const language = sourceLanguageForToken(info);
  const lemma = language === "hebrew" && info.surface
    ? info.surface
    : (info.lemma || info.surface || "");
  void createInvestigationFromLemma({
    lemma,
    strongs: info.strongs,
    language,
    reference: info.reference || currentPhrase()?.reference,
    clause: phraseGreekText(currentPhrase()),
    surface: info.surface,
    ble: info.rendering,
    book: state.bookId === "daniel" ? "Daniel" : ""
  }).catch(error => {
    prototypeMessage.textContent = error.message || "Could not create investigation.";
  });
});

document.addEventListener("click", event => {
  if (decisionPanel.hidden) return;
  if (event.target instanceof Node && decisionPanel.contains(event.target)) return;
  hideGreekDecisionPanel();
});

translationView.addEventListener("scroll", hideGreekDecisionPanel);
window.addEventListener("resize", hideGreekDecisionPanel);

investigationToggle.addEventListener("click", () => {
  setInvestigationListOpen(!document.body.classList.contains("investigations-open"));
});

newInvestigationButton?.addEventListener("click", () => {
  openNewInvestigationModal();
});

cancelNewInvestigationButton?.addEventListener("click", () => {
  closeNewInvestigationModal();
});

createNewInvestigationButton?.addEventListener("click", () => {
  void submitNewInvestigationModal().catch(error => {
    if (newInvestigationMessage) {
      newInvestigationMessage.textContent = error.message || "Could not create investigation.";
    }
  });
});

newInvestigationModal?.addEventListener("click", event => {
  if (event.target === newInvestigationModal) closeNewInvestigationModal();
});

gatherEvidence.addEventListener("click", () => {
  openGatherModal();
});

backToTranslation.addEventListener("click", () => {
  void returnToTranslation().catch(error => {
    prototypeMessage.textContent = error.message || "Return error.";
  });
});

previousPhrase.addEventListener("click", () => {
  void movePhrase(-1);
});

nextPhrase.addEventListener("click", () => {
  void movePhrase(1);
});

referenceJumpForm?.addEventListener("submit", event => {
  event.preventDefault();
  void jumpToReference(referenceJumpInput?.value || "");
});

analyzeGatesButton.addEventListener("click", () => {
  void analyzeCurrentPhrase({ force: true }).catch(error => {
    prototypeMessage.textContent = error.message || "Gate analysis error.";
  });
});

assistGatesButton.addEventListener("click", () => {
  void assistCurrentPhrase().catch(error => {
    prototypeMessage.textContent = error.message || "AI assist error.";
  });
});

acceptDraftButton.addEventListener("click", () => {
  acceptConstrainedDraft();
});

openGateInvestigationButton.addEventListener("click", () => {
  const id = openGateInvestigationButton.dataset.investigationId;
  if (id) {
    void openInvestigation(id);
    return;
  }
  const lemma = openGateInvestigationButton.dataset.blockedLemma || "";
  const strongs = openGateInvestigationButton.dataset.blockedStrongs || "";
  if (!lemma && !strongs) {
    void openInvestigation(state.investigation || "INV-56-0003");
    return;
  }
  void createInvestigationFromLemma({
    lemma: lemma || strongs,
    strongs,
    reference: currentPhrase()?.reference,
    clause: phraseGreekText(currentPhrase()),
    surface: lemma,
    ble: ""
  }).catch(error => {
    prototypeMessage.textContent = error.message || "Could not create investigation.";
  });
});

openInvestigationsMenuButton?.addEventListener("click", async () => {
  await loadInvestigations();
  setInvestigationListOpen(true);
  sidebar.hidden = false;
});

openFinalizationButton?.addEventListener("click", () => {
  void showFinalizationView().catch(error => {
    setPhraseSaveStatus(error.message || "Could not open the final book step.", "error");
  });
});

closeFinalizationButton?.addEventListener("click", () => {
  showTranslationView();
});

runGather.addEventListener("click", () => {
  void runEvidenceGather().catch(() => {});
});

replaceEvidence.addEventListener("click", () => {
  void runEvidenceGather({ replace: true }).catch(() => {});
});

cancelGather.addEventListener("click", () => {
  closeGatherModal();
});

cancelReplace.addEventListener("click", () => {
  closeGatherModal();
});

verifyTranslationButton?.addEventListener("click", () => {
  void runWorkflowAction("verify", "translation");
});

continueAlignmentButton?.addEventListener("click", () => {
  showTranslationView();
  void openNextAlignmentWork();
});

approveTranslationButton?.addEventListener("click", () => {
  openWorkflowApproval("translation");
});

verifyAlignmentButton?.addEventListener("click", () => {
  void runWorkflowAction("verify", "alignment");
});

approveAlignmentButton?.addEventListener("click", () => {
  openWorkflowApproval("alignment");
});

reviewCommitButton?.addEventListener("click", openWorkflowCommit);

exportBookButton?.addEventListener("click", () => {
  void runWorkflowAction("export");
});

publishBookButton?.addEventListener("click", openWorkflowPublish);

cancelWorkflowApproval?.addEventListener("click", closeWorkflowApproval);
confirmWorkflowApproval?.addEventListener("click", () => {
  void submitWorkflowApproval();
});
workflowApprovalModal?.addEventListener("click", event => {
  if (event.target === workflowApprovalModal) closeWorkflowApproval();
});
cancelWorkflowCommit?.addEventListener("click", closeWorkflowCommit);
confirmWorkflowCommit?.addEventListener("click", () => {
  void submitWorkflowCommit();
});
workflowCommitModal?.addEventListener("click", event => {
  if (event.target === workflowCommitModal) closeWorkflowCommit();
});
cancelWorkflowPublish?.addEventListener("click", closeWorkflowPublish);
confirmWorkflowPublish?.addEventListener("click", () => {
  void submitWorkflowPublish();
});
workflowPublishModal?.addEventListener("click", event => {
  if (event.target === workflowPublishModal) closeWorkflowPublish();
});
copyPublicationCommand?.addEventListener("click", () => {
  void copyPublisherPushCommand();
});

cancelAlignmentEdit?.addEventListener("click", closeAlignmentEditor);
saveAlignmentEdit?.addEventListener("click", () => {
  void saveCurrentAlignmentEdit().catch(error => {
    setPhraseSaveStatus(error.message || "Alignment save failed", "error");
  });
});
confirmAlignmentPhrase?.addEventListener("click", () => {
  void confirmCurrentAlignmentPhrase().catch(error => {
    setPhraseSaveStatus(error.message || "Phrase confirmation failed", "error");
  });
});

gatherModal.addEventListener("click", event => {
  if (event.target === gatherModal) {
    closeGatherModal();
  }
});

function isEditableKeyTarget(target) {
  if (!(target instanceof HTMLElement)) return false;
  if (target.isContentEditable) return true;
  const tag = target.tagName;
  return tag === "TEXTAREA" || tag === "INPUT" || tag === "SELECT";
}

function phraseNavDirection(event) {
  if (state.view !== "translation") return 0;
  const code = event.code;
  const key = event.key;
  const mod = event.metaKey || event.ctrlKey;

  // Reliable on Mac (works in textarea; capture handler runs first):
  // Control+, / Control+.  and  ⌘⇧← / ⌘⇧→
  if (event.ctrlKey && !event.metaKey && !event.altKey && !event.shiftKey) {
    if (key === "," || code === "Comma") return -1;
    if (key === "." || code === "Period") return 1;
  }
  if (event.metaKey && event.shiftKey && !event.altKey && !event.ctrlKey) {
    if (code === "ArrowLeft" || key === "ArrowLeft") return -1;
    if (code === "ArrowRight" || key === "ArrowRight") return 1;
  }
  // When not typing in an input: plain arrows, or k/j (prev/next)
  if (!mod && !event.altKey && !event.shiftKey && !isEditableKeyTarget(event.target)) {
    if (code === "ArrowLeft" || key === "ArrowLeft" || key === "k" || key === "K") return -1;
    if (code === "ArrowRight" || key === "ArrowRight" || key === "j" || key === "J") return 1;
  }
  return 0;
}

window.addEventListener("keydown", event => {
  if (event.key === "Escape" && workflowPublishModal && !workflowPublishModal.hidden) {
    closeWorkflowPublish();
    return;
  }

  if (event.key === "Escape" && workflowCommitModal && !workflowCommitModal.hidden) {
    closeWorkflowCommit();
    return;
  }

  if (event.key === "Escape" && workflowApprovalModal && !workflowApprovalModal.hidden) {
    closeWorkflowApproval();
    return;
  }

  if (event.key === "Escape" && alignmentEditor && !alignmentEditor.hidden) {
    closeAlignmentEditor();
    return;
  }

  if (event.key === "Escape" && newInvestigationModal && !newInvestigationModal.hidden) {
    closeNewInvestigationModal();
    return;
  }

  if (event.key === "Escape" && !gatherModal.hidden) {
    closeGatherModal();
    return;
  }

  const mod = event.metaKey || event.ctrlKey;
  if (mod && event.key.toLowerCase() === "s") {
    event.preventDefault();
    if (state.view === "translation") {
      void flushTranslationSave();
    } else {
      void saveCurrent();
    }
    return;
  }
}, true);

// Capture phase so Mac textarea word-jump / browser shortcuts don't swallow nav.
window.addEventListener("keydown", event => {
  const direction = phraseNavDirection(event);
  if (!direction) return;
  event.preventDefault();
  event.stopPropagation();
  void movePhrase(direction);
}, true);

window.addEventListener("beforeunload", event => {
  if (state.view === "translation") {
    syncTranslationDocumentFromEditor();
    navigator.sendBeacon?.(
      translationApiPath("/api/translation/current"),
      new Blob([JSON.stringify({
        book: state.bookId,
        content: buildTranslationDocument(),
        phrases: serializePhraseRecords()
      })], { type: "application/json" })
    );
  }

  if (!state.dirty) return;
  event.preventDefault();
});

async function openInitialRoute() {
  if (window.location.hash.startsWith("#investigation/")) {
    await openInvestigation(readInvestigationIdFromHash());
    return;
  }

  showTranslationView();
  sidebar.hidden = false;
}

function readInvestigationIdFromHash() {
  const match = window.location.hash.match(/^#investigation\/(INV-\d{2}-\d{4})$/);
  return match?.[1] || state.investigation;
}

window.addEventListener("hashchange", () => {
  if (window.location.hash.startsWith("#investigation/")) {
    void openInvestigation(readInvestigationIdFromHash()).catch(error => {
      prototypeMessage.textContent = error.message || "Investigation load error.";
    });
  }
});

if (new URLSearchParams(window.location.search).get("view") === "finish") {
  // Book publication uses canonical files and does not require legacy phrase seeds.
  // Never initialize the phrase editor (or its save hooks) in this entry point.
  state.view = "finalization";
  closeFinalizationButton.hidden = true;
  await loadBookWorkflow();
  await showFinalizationView();
} else {
  await loadInvestigations();
  renderTabs();
  await loadAvailableBooks();
  await loadTranslationDocument();
  await loadBookWorkflow();
  await Promise.all([
    enrichPhraseReferencesFromUnits(),
    loadContinuationUnits(),
    loadAiAvailability()
  ]);
  state.phraseIndex = firstIncompletePhraseIndex();
  renderTranslationPhrase();
  await loadApprovedDecisions({ applyToText: !state.translationLoadedFromDisk });
  await openInitialRoute();
}

bookSelect?.addEventListener("change", async () => {
  if (isTranslationDirty()) {
    try {
      await flushTranslationSave();
    } catch (error) {
      prototypeMessage.textContent = error.message || "Translation save error.";
      bookSelect.value = state.bookId;
      return;
    }
  }
  state.bookId = bookSelect.value;
  const url = new URL(window.location.href);
  url.searchParams.set("book", state.bookId);
  window.history.replaceState(null, "", `${url.pathname}?${url.searchParams.toString()}`);
  state.phraseIndex = 0;
  state.translationLoadedFromDisk = false;
  translationUnitsLoaded = false;
  translationUnits = [];
  await loadInvestigations();
  await loadTranslationDocument();
  await loadBookWorkflow();
  await enrichPhraseReferencesFromUnits();
  await loadContinuationUnits({ force: true });
  state.phraseIndex = firstIncompletePhraseIndex();
  renderTranslationPhrase();
});
