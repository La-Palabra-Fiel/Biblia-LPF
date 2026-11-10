# STEPBible lexicon provenance

Verified: 2026-10-21

Upstream repository: `https://github.com/STEPBible/STEPBible-Data`

Upstream ref checked: `master`

Upstream commit: `ed476a8ee6e3f7b3a46fc48af6c7dabc02387b1d`

Upstream commit date: `2026-10-17T16:22:28Z`

Each local file's Git blob ID exactly matched the corresponding file returned
by the GitHub Contents API at the ref above.

| File | SHA-256 | Git blob | LBF status |
| --- | --- | --- | --- |
| `TBESG - Translators Brief lexicon of Extended Strongs for Greek - STEPBible.org CC BY.txt` | `312f723d7b8ef263bbdfb0451c9b8057125804dfff390b6f8544cff2a84b57f4` | `efe271a1dbb73fa01f8fa6e0f164c6687757a9ae` | Authorized through the fail-closed parser; Robinson lexical-ID coverage validated |
| `TBESH - Translators Brief lexicon of Extended Strongs for Hebrew - STEPBible.org CC BY.txt` | `464dccadd95fd8620dd05fa0d7a4caba58ec3c4d5db3ebf38e43d046ca25b591` | `a64990a674d13245ae1e9ed426bc69197c2fbad5` | Blocked: its header requires Online Bible permission for the meaning fields |
| `TFLSJ  0-5624 - Translators Formatted full LSJ Bible lexicon - STEPBible.org CC BY.txt` | `fcc2845412132a7bb91fc3dbb5a544c807daf57e4791c4d9af61efe209e97691` | `db44789a0b3523ad00ba2c93c6fe78ad3db1b4bb` | Present but not approved for LBF |
| `TFLSJ extra - Translators Formatted full LSJ Bible lexicon - STEPBible.org CC BY.txt` | `fdb2840067faa11301b208a343a9453fbe40b367e94eac981071261626201bc2` | `cee6c1207d68beac2fcd66a7dbbd798803658e73` | Present but not approved for LBF |

The upstream files carry their own licensing and attribution notices. This
manifest records provenance; it does not broaden those permissions.

## Open Scriptures HebrewLexicon

Verified: 2026-10-21

Upstream repository: `https://github.com/openscriptures/HebrewLexicon`

Pinned upstream commit: `21c9add13bc727d3a951361778e97e3ff7afd1ce`

License: CC BY 4.0. The upstream `readme.md` states that the actual BDB and
Strong dictionary text remains in the public domain and requests attribution
to the Open Scriptures Hebrew Bible Project.

The local files below matched the raw files at that exact commit byte for
byte:

| File | SHA-256 |
| --- | --- |
| `HebrewLexicon-master/AugIndex.xml` | `e7217ca8ff8ff3f21f9cf1bbe87411adf55f6aa88bcf5ed9ddc886cc6b160c5d` |
| `HebrewLexicon-master/BrownDriverBriggs.xml` | `2b52658a4323d91674cda4090ab8b3ebddfff640f4f18143c28300e80b2c38f8` |
| `HebrewLexicon-master/LexicalIndex.xml` | `8f7a605c58899d2f44430149c143c00903976e1e91232476677972a69e5bc85f` |
| `HebrewLexicon-master/HebrewStrong.xml` | `a628f4f89f8bdaf2483fd3faf1abc8653cc6717758dfc9f24beb7571d9bdd0c4` |
| `HebrewLexicon-master/readme.md` | `9a129c25674387c494571c3828aa3a8eb78459c165e275c313ae26994ce8ff22` |

LBF uses `AugIndex.xml`, `LexicalIndex.xml`, and
`BrownDriverBriggs.xml` through the fail-closed loader in
`tools/pipeline/hebrew_lexicon.py`. The lexicon records possible senses only;
it has no authority to select the contextual sense.
