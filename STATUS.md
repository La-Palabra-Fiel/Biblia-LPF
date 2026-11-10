# STATUS

This ledger is not the translation process. Spanish is produced by
`tools/pipeline/`: Cursor Auto drafts and audits; Sonnet steps in only
when a verse is questionable. `tools/verify.py` does not decide the Spanish.

Four states: `none` | `draft` | `ready` | `done`.
How to work: `tools/pipeline/README.md`. How the data may live: `DATA_CONTRACT.md`.

`ready` is written only by `python3 tools/verify.py`. That means the checks
passed. You still approve.

`done` requires a named human on this file **and** a passing `python3 tools/status.py`.

Signed columns stay empty until a human writes a name and an ISO date.

| book | testament | translation | alignment | translation_by | translation_on | alignment_by | alignment_on | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| genesis | ot | draft | draft |  |  |  |  | names pass 2026-09-19 — re-approve |
| exodo | ot | draft | none |  |  |  |  | Yahvé standardized; chapters under named human review |
| levitico | ot | draft | none |  |  |  |  | names pass 2026-09-19 |
| numeros | ot | draft | none |  |  |  |  | names pass 2026-09-19 |
| deuteronomio | ot | draft | none |  |  |  |  | names pass 2026-09-19 |
| josue | ot | draft | none |  |  |  |  | names pass 2026-09-19 |
| jueces | ot | draft | none |  |  |  |  | names pass 2026-09-19 |
| rut | ot | draft | none |  |  |  |  | names pass 2026-09-19 |
| 1samuel | ot | draft | none |  |  |  |  | names pass 2026-09-19 |
| 2samuel | ot | draft | none |  |  |  |  | names pass 2026-09-19 |
| 1reyes | ot | draft | none |  |  |  |  | names pass 2026-09-19 |
| 2reyes | ot | draft | none |  |  |  |  | names pass 2026-09-19 |
| 1cronicas | ot | draft | none |  |  |  |  | names pass 2026-09-19 |
| 2cronicas | ot | draft | none |  |  |  |  | names pass 2026-09-19 |
| esdras | ot | draft | none |  |  |  |  | names pass 2026-09-19 |
| nehemias | ot | draft | none |  |  |  |  | names pass 2026-09-19 |
| ester | ot | draft | none |  |  |  |  | names pass 2026-09-19 |
| job | ot | draft | none |  |  |  |  | names pass 2026-09-19 |
| salmos | ot | draft | none |  |  |  |  | names pass 2026-09-19 |
| proverbios | ot | draft | none |  |  |  |  | names pass 2026-09-19 |
| eclesiastes | ot | draft | none |  |  |  |  | names pass 2026-09-19 |
| cantares | ot | draft | none |  |  |  |  | names pass 2026-09-19 |
| isaias | ot | ready | draft |  |  |  |  |  |
| jeremias | ot | draft | none |  |  |  |  |  |
| lamentaciones | ot | ready | none |  |  |  |  |  |
| ezequiel | ot | ready | none |  |  |  |  |  |
| daniel | ot | ready | draft |  |  |  |  | file exists; gloss maps are not alignment |
| oseas | ot | ready | none |  |  |  |  |  |
| joel | ot | ready | none |  |  |  |  |  |
| amos | ot | ready | none |  |  |  |  |  |
| abdias | ot | ready | none |  |  |  |  |  |
| jonas | ot | ready | none |  |  |  |  |  |
| miqueas | ot | ready | none |  |  |  |  |  |
| nahum | ot | ready | none |  |  |  |  |  |
| habacuc | ot | done | done | John Wry | 2026-11-06 | John Wry | 2026-11-06 |  |
| sofonias | ot | ready | none |  |  |  |  |  |
| hageo | ot | ready | none |  |  |  |  |  |
| zacarias | ot | ready | draft |  |  |  |  | 211 `mapped`; AI audit pass (93/118/0; 9:17 H1715 false-fail overruled) — unsiged pending repair |
| malaquias | ot | ready | none |  |  |  |  |  |
| mateo | nt | ready | none |  |  |  |  |  |
| marcos | nt | ready | none |  |  |  |  |  |
| lucas | nt | ready | none |  |  |  |  |  |
| juan | nt | ready | none |  |  |  |  |  |
| hechos | nt | ready | none |  |  |  |  |  |
| romanos | nt | ready | none |  |  |  |  |  |
| 1corintios | nt | ready | none |  |  |  |  |  |
| 2corintios | nt | ready | none |  |  |  |  |  |
| galatas | nt | ready | none |  |  |  |  |  |
| efesios | nt | ready | none |  |  |  |  |  |
| filipenses | nt | draft | draft |  |  |  |  | reclasificado como borrador por decisión humana 2026-11-09; el trabajo anterior se produjo para un propósito específico y no constituye aprobación final |
| colosenses | nt | ready | none |  |  |  |  |  |
| 1tesalonicenses | nt | ready | none |  |  |  |  |  |
| 2tesalonicenses | nt | ready | none |  |  |  |  |  |
| 1timoteo | nt | ready | none |  |  |  |  |  |
| 2timoteo | nt | ready | none |  |  |  |  |  |
| titus | nt | done | draft | John Wry | 2026-08-20 |  |  | mixed hand + auto-zip; auto is not finished |
| filemon | nt | ready | none |  |  |  |  |  |
| hebreos | nt | ready | none |  |  |  |  |  |
| santiago | nt | ready | none |  |  |  |  |  |
| 1pedro | nt | ready | none |  |  |  |  |  |
| 2pedro | nt | ready | none |  |  |  |  |  |
| 1juan | nt | ready | draft |  |  |  |  | reverse-links claim all-hand; unsigned |
| 2juan | nt | ready | none |  |  |  |  |  |
| 3juan | nt | ready | none |  |  |  |  |  |
| judas | nt | ready | ready |  |  |  |  | reverse-links claim all-hand; unsigned |
| apocalipsis | nt | draft | draft |  |  |  |  | reclasificado como borrador por decisión humana 2026-11-09; revisión TR posterior no comprobada y el trabajo anterior no constituye aprobación final |

## Open human decisions

Nehemiah 7:68: OSHB/WLC has no source for this Protestant label (WLC Neh 7:68 is Protestant 7:69). First-pass may draft it only from Ezra 2:66 OSHB after explicit confirmation. Still draft until second-pass review. Apocalipsis Spanish: later TR revision accepted. Zacarías 11:2: `el cedro` already applied.

Zacarías (2026-09-16): translation + alignment both `done` (John Wry). Alignment path: structural map accept → AI audit pass → human approval.
