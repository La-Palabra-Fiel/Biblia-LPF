# Source Mapping and Provenance

Status: design/investigation record, 2026-09-09. This file sets no completed translation or alignment status.

## Authority map

```text
OT text/morphology: OSHB ──┐
                            ├── OT syntax dataset
OT syntax analysis: MACULA Hebrew ─┘

NT text: Robinson UTR Scrivener TR1894 surface ─┐
NT morphology: Robinson tags in the same UTR record ─┼── TR1894 syntax dataset
NT text check: Scrivener SCV distribution ──────┘
NT syntax decisions: documented ─┘

MACULA Greek (N1904/SBLGNT) ── reference, comparison, validation only
```

The direction matters. MACULA Greek may suggest a construction to review, but it must never furnish the NT text layer, token identity, or an undocumented clause boundary for TR1894.

## OT: OSHB → MACULA Hebrew

| Layer | Authoritative value | Required persisted identity | Notes |
| --- | --- | --- | --- |
| Text | OSHB/WLC source representation selected by project policy | source system and token/morpheme ID | Do not replace source identity with a display index. |
| Morphology | OSHB native morphology | raw OSHB code plus normalized features if derived | Preserve native code unchanged. |
| Syntax | MACULA Hebrew nodes | MACULA `xml:id` terminal link and syntax-node provenance | `Node[Cat="CL"]` / `wg[class="cl"]` supply existing OT clause analysis. |
| Cross-source mapping | MACULA mapping files | explicit mapping record and cardinality | Never infer a map from ordinal position; Qere/Kethiv and morphemes prevent that. |

MACULA Hebrew exposes a direct OSHB morpheme linkage: OSHB/OpenScriptures `<m n="010010010011">` becomes MACULA `morphId="010010010011"` and terminal `xml:id="o010010010011"`. These identities are mechanically related but represent distinct layers; persist the original OSHB `m/@n` as the source morpheme ID and the MACULA `xml:id` as the syntax-terminal identifier.

## NT: TR1894 → proposed syntax

### Available machine-readable TR resources

The authoritative NT source is the local project directory
`source/greek/TR1894/`. In accordance with `SOURCE_POLICY.md`, the pinned
`robinson-parsed/*.UTR` records are the working Scrivener TR1894 surface and
Robinson morphology layer. The independently pinned
`scrivener-textonly/*.SCV` records verify that surface. `tr1894.txt` is a
legacy Unicode display resource; it cannot replace a UTR reading or token
boundary.

| Resource | Format | Content | Identifier situation |
| --- | --- | --- | --- |
| `robinson-parsed/*.UTR` | beta-code parsed text | **Canonical working TR1894 token sequence**, Strong's, Robinson morphology | Book/chapter/verse labels and deterministic token order |
| `scrivener-textonly/*.SCV` | beta-code plain text | Independent check of the same Scrivener 1894 edition | Whole-verse verification; no morphology |
| `tr1894.txt` | pipe-delimited verse text, Unicode Greek | Legacy display resource | Not allowed to override UTR surface or order |
| `honza/textus-receptus` | flat/nested JSON, XML, YAML | Accented text, grammar, Strong's, dictionary form, glosses | Ordered word objects; inspect and pin a commit before production use |

The local source records pinned upstream commits: `greektext-scrivener` `6049a43b135ed870f843b83eb6a04764fc796678` (text-only) and `greektext-textus-receptus` `7fd4d02c3e5adebd379ebfbc824040820dde10fc` (parsed). Its README correctly warns that parsed Robinson material is a helper and that text differences must be evaluated against Scrivener 1894.

The user-named `honza/textus-receptus` repository advertises 1894 Scrivener text in `gnt.flat.{json,xml,yaml}` and `gnt.nested.{json,xml,yaml}`, with grammar, Strong's, lemma/dictionary form, and glosses. It remains external research/reference material only: it is not an NT text source for this dataset unless the user explicitly changes this source decision. No files from it have been imported by this investigation.

### Stable TR token rule

TR source files do not expose a universal stable terminal ID. Generate one deterministically from fixed Protestant reference and source-token ordinal:

```text
<BOOK>.<chapter>.<verse>.w<3-digit ordinal>
MAT.1.1.w001
MAT.1.1.w008
```

Each token must also store `source_ref`, `source_ordinal`, `source_revision`,
exact UTR `surface_beta`, optional deterministic `surface_unicode`, and a
source file/record/token `source_locator`. An ID is stable only within its
pinned source revision and documented tokenization policy. Do not renumber it
to match MACULA, and do not make punctuation into a word token merely to make
another edition's counts fit.

### TR text/morphology reconciliation gate

The local sources deliberately supply different capabilities: Scrivener text-only is the direct text witness; UTR supplies token-level morphology. Before production, make one versioned reconciliation table:

| Outcome | Action |
| --- | --- |
| Same UTR/SCV token boundary and reading | Accept the UTR token and Robinson morphology; record the SCV whole-verse check. |
| Same reading, representational difference only | Record the reversible normalization rule; preserve source surfaces. |
| Alternate reading, insertion/deletion, or split/merge | Create an explicit one-to-one/one-to-many mapping and require human review. Do not borrow another edition's word. |
| Unresolved | Leave morphology/linkage unresolved and block the affected syntax export. |

This is an engineering gate, not authorization to import automatically. It protects TR1894 as immutable NT text authority.

## MACULA Greek: comparison only

A MACULA Greek ID such as `n40001005005` belongs to its edition. If retained, it must occur only in a reference record:

```json
{
  "reference_dataset": "macula-greek/Nestle1904",
  "reference_revision": "pinned checkout revision",
  "reference_terminal_id": "n40001005005",
  "relation": "comparison-only",
  "basis": "same reference position; text differs"
}
```

A reference link is not a token identity mapping and confers no syntax approval. It is permitted only after a TR tokenization comparison records the relationship.

The production comparison gate is stricter than a same-reference link. A
MACULA terminal can anchor a candidate branch only when its normalized Greek
surface agrees with both the SCV token and one Robinson token, and the match is
forced in the same order. SCV/Robinson spelling adjudications and token merges
remain valid in the morphology layer but cannot serve as MACULA anchors. Any
two-source match or ambiguous repeated-word match stays `HOLD`.

## Reproducibility requirements

Every transformation needs a manifest containing input path, commit/content
hash, command/version, output hash, and unresolved mapping count. A TR verse
must reconstruct from its pinned UTR record alone, and every syntax terminal
must reach a TR `token_id` without consulting MACULA Greek. The generated
`source/greek/TR1894/MANIFEST.json` and
`tr1894-robinson-reconciliation.json` bind this source layer;
`schema/tr1894-syntax.schema.json` is the proposed machine-checkable boundary
for the later syntax layer.

The text/morphology reconciliation was completed on 2026-11-09: all 7,957
verses and 140,655 SCV-authoritative tokens are accounted for, with every
token bound to Robinson morphology and no unresolved source rows. Human
decisions are retained in `source/greek/TR1894/ADJUDICATIONS.json`.
