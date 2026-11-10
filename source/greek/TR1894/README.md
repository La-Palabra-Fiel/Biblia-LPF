# Scrivener 1894 Textus Receptus (LBF Greek source)

LBF’s New Testament textual basis is **F. H. A. Scrivener’s 1894 Textus Receptus**.

This folder holds the machine-readable TR sources used for translation and
alignment. MorphGNT/SBLGNT remains a helper only and must not override TR.

## Contents

| Path | What | License |
|------|------|---------|
| `tr1894.txt` | Existing verse-level accented Scrivener 1894 (legacy import) | Treat as TR text |
| `scrivener-textonly/` | Maurice A. Robinson distribution of Scrivener 1894 (unparsed, beta code) | Public Domain |
| `robinson-parsed/` | Maurice A. Robinson TR with morphological tags + Strong’s (beta code; `.UTR`) | Public Domain |

## Preferred working source

For LBF tooling (token spine, morph, reverse-interlinear prep), prefer:

**`robinson-parsed/*.UTR`**

`MANIFEST.json` pins every UTR and SCV input by checksum.
`tr1894-robinson-reconciliation.json` records the deterministic whole-verse
comparison. Generate both with `python3 tools/build_nt_source.py`. A `hold`
entry is deliberately unresolved and must not be repaired by choosing a text
automatically.

Current validated result (2026-11-09): 7,957 verses, 140,655 canonical SCV
tokens, 140,655 Robinson morphology bindings, zero `REVIEW`, and zero `HOLD`.
The authoritative human decisions are recorded in `ADJUDICATIONS.json`.

Format (Robinson / ByzTxt):

```text
1:1 word 1234 {N-NSM} word 1234 {V-PAI-3S} ...
```

- Surface forms are **beta code** (not Unicode Greek)
- Strong’s numbers are bare digits (e.g. `2316` = G2316)
- Morph codes are in `{...}` (Robinson parsing codes)
- Occasional Stephens/Scrivener alternates may appear as `| formA | formB |`

Unparsed Scrivener text for cross-check: **`scrivener-textonly/*.SCV`**.

## Provenance

- Parsed TR: https://github.com/byztxt/greektext-textus-receptus  
  Commit: see `robinson-parsed/SOURCE-COMMIT.txt`
- Scrivener text: https://github.com/byztxt/greektext-scrivener  
  Commit: see `scrivener-textonly/SOURCE-COMMIT.txt`
- Upstream maintainer: Ulrik Sandborg-Petersen / ByzTxt  
- Primary editor: Dr. Maurice A. Robinson  

Upstream READMEs are copied beside each tree as `SOURCE-README.md`.

## Notes for LBF

1. Do not replace Scrivener with Robinson-Pierpont Byzantine Majority Text.
2. When `robinson-parsed` and `tr1894.txt` disagree, evaluate against Scrivener 1894
   (and document the decision).
3. MorphGNT may supply lemma/morph only where TR tokens align; TR readings win.
