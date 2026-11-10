# NOTICE

Copyright (c) 2026 Cultivados en Gracia y Verdad

La Biblia Fiel (LBF) is owned by Cultivados en Gracia y Verdad
(https://github.com/Cultivados-en-Gracia-y-Verdad). This file records
third-party works bundled in the repository and material that is not
licensed here.

## LBF Spanish

The LBF translation and its published releases are licensed as described
in `LICENSE` (CC BY-NC-ND 4.0 for the Bible text; commercial use by
written agreement with Cultivados en Gracia y Verdad).

Attribution for the LBF text:

> La Biblia Fiel. © Cultivados en Gracia y Verdad.
> Licensed under CC BY-NC-ND 4.0.
> https://github.com/Cultivados-en-Gracia-y-Verdad/Biblia-LBF

## Third-party sources

This repository includes original-language sources used to produce LBF.
Those files keep their own licenses. LBF does not claim them.

### Open Scriptures Hebrew Bible / Westminster Leningrad Codex

Path: `source/hebrew/OSHB/`

The Westminster Leningrad Codex is in the public domain. The Open
Scriptures Hebrew Bible morphology and related work is licensed under
Creative Commons Attribution 4.0 International (CC BY 4.0).

See `source/hebrew/OSHB/morphhb/LICENSE.md`.

Required attribution:

> Original work of the Open Scriptures Hebrew Bible available at
> https://github.com/openscriptures/morphhb

### Scrivener 1894 Textus Receptus

Path: `source/greek/TR1894/`

Maurice A. Robinson’s distributions of Scrivener 1894 (text-only and
morphologically tagged) are treated as public domain. See
`source/greek/TR1894/README.md` and the `SOURCE-README.md` files in that
tree.

### STEPBible TBESH / TBESG

Approved source repository:
`https://github.com/STEPBible/STEPBible-Data`, directory `Lexicons/`.

The repository presents these files under Creative Commons Attribution 4.0
International (CC BY 4.0). However, TBESH's own header states that its meaning
fields are based on the Abridged BDB by Online Bible and that permission should
be obtained from Online Bible before applying those definitions in a project.
TBESH's `Meaning` field is therefore blocked pending written permission or
replacement. LBF does not read that field. Other TBESH fields remain excluded
until a positive-allowlist parser and leakage tests are approved.

TBESG is an authorized secondary source for the NT evidence packet through the
repository's fail-closed positive-allowlist parser. Its exact upstream commit,
checksum, license, attribution, and Robinson lexical-ID coverage are validated
before use. Locally present TFLSJ files are not approved by this notice.

### Open Scriptures HebrewLexicon

Path: `Lexicons/HebrewLexicon-master/`

The files are released under Creative Commons Attribution 4.0 International
(CC BY 4.0). The upstream notice states that the actual Brown-Driver-Briggs and
Strong dictionary text remains in the public domain.

Required attribution:

> Open Scriptures Hebrew Bible Project

The exact upstream commit and local checksums are recorded in
`Lexicons/PROVENANCE.md`.

### MACULA Hebrew Linguistic Datasets

Path: `source/hebrew/macula-hebrew-main/`

The allowlisted structural syntax data is used under CC BY 4.0. Required
attribution: “MACULA Hebrew Linguistic Datasets, available at
https://github.com/Clear-Bible/macula-hebrew/”. LBF excludes MACULA glosses,
translations, LXX equivalents, SDBH fields, semantic domains, frames, and
word-sense selections. The pinned commit, manifest checksum, and exact allowed
surface are recorded in `source/hebrew/MACULA_PROVENANCE.md`.

## Not in this repository

The reverse-alignment engine and its working database are private.
They are not published here and are not offered under `LICENSE`.

Production workshops, verification records, and internal translator
tooling live outside this repository.

## Names

“La Biblia Fiel”, “LBF”, and “Cultivados en Gracia y Verdad” identify
the published wording and the owning project. They are not a license
to publish an altered text under those names.
