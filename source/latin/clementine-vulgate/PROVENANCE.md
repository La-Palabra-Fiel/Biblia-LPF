# Provenance: Clementine Latin reception control

This directory records one **historical reception** control. The Clementine
Vulgate is not a textual authority for LPF, is not evidence for the original
meaning of the Hebrew or Greek, and is not an input to the automatic
translation packet.

## Pinned source

- repository: `https://bitbucket.org/clementinetextproject/text.git`;
- commit: `edc85da058be630183d26e4deb6714ade80e600c` (22 October 2022);
- root tree: `43d059c73fb2f96264670ce64fb304aea5785fc2`;
- selected files: the 73 tracked root-level `*.lat` files;
- aggregate Git-blob hash:
  `df9ba8f9d951d949041bfc4721e3a0ddd946b2335fa7b7c9647ed9c539a2d1c4`;
- encoding: Windows-1252;
- electronic edition: Clementine Vulgate Project, based on Colunga-Turrado
  1947 and Vercellone 1861.

The historical text and the project's transcription are identified as public
domain by the Clementine Vulgate Project's distribution notices. The related
VulSearch software is GPL-2.0. LPF does not redistribute the source files;
this directory retains only provenance and reviewable derived concordances.

## Method and limits

[`clementine_latin_inventory.py`](../../../tools/research/clementine_latin_inventory.py)
refuses a checkout at any other commit, with a different tree, a dirty state,
an altered file count or an altered aggregate blob hash. It decodes the pinned
files as Windows-1252 and searches normalized surface prefixes. Every hit
retains the printed surface, book file, verse label and complete source line.
It assigns no Latin lemma, Spanish gloss or semantic category.

This edition is a late ecclesiastical witness useful for tracing Latin and
later Spanish terminology. It must not be described as a critical
reconstruction of Jerome's earliest text, much less as first-century evidence.
Its lexical choices may reveal mediation; they cannot decide an LPF rendering.

