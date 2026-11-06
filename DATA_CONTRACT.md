# Biblia-LBF Data Contract

Status: normative

## Purpose

`Biblia-LBF` is the only editable source of truth for LPF. `LBF` remains the
historical technical identifier in repository names, schemas, filenames, and
consumer paths; it is not the current public name.
It owns the Spanish text, the source-to-Spanish alignment, and the
record of whether that work is finished.

Working format:

- one Markdown file per book for Spanish
- one reverse-links file per book for alignment
- `STATUS.md` for finished

## Canonical homes

| Data | Path |
| --- | --- |
| Spanish | `translation/{nt\|ot}/{book}.md` |
| Alignment | `alignment/{nt\|ot}/{book}/{book}-reverse-links.json` |
| Status | `STATUS.md` |
| Sources | `source/` |

Every editable verse exists once. Every editable alignment exists once.
Verse labels are Protestant. Token IDs are persisted. Alignments name
token IDs, not character offsets as the source of truth.

Canonical alignment surfaces contain words only. Punctuation, quotation
marks, exclamation and question marks, and Markdown emphasis markers belong
to the Spanish translation, never to a reverse-link `surface`. When
punctuation separates words that cite the same source token, the canonical
alignment uses separate lexical units with the same `sourceTokenIds`; its
character spans cover only the words and intervening whitespace inside each
unit.

## Source boundary

`SOURCE_POLICY.md` is normative. Translation, audit, and alignment may use
only the canonical per-verse packet and the evidence explicitly authorized
there. A packet with a different policy identifier, textual basis, or source
allowlist must be rejected before a model call. Insufficient evidence produces
`HOLD`; it never authorizes another Bible, lexicon, commentary, web lookup,
retrieval tool, or remembered traditional rendering.

Its seven-level evidence hierarchy is mandatory. Lower levels never override
higher levels; GPT proposes and cites, while only a human adjudicates uncertain
or disputed cases. A model pass cannot substitute for that adjudication.

## Finished

`STATUS.md` is the only ledger. Four states:
`none` | `draft` | `ready` | `done`.

| State | Who writes it | Meaning |
| --- | --- | --- |
| `none` | `python3 tools/verify.py` | No real file |
| `draft` | a person, or `verify.py` | Work exists. Not complete |
| `ready` | `python3 tools/verify.py` only | Checks passed. Awaiting approval |
| `done` | a named human, directly or through Translator's explicit approval control | Approved |

`done` requires a name, a date, and a passing `python3 tools/status.py`.
`verify.py` never writes `done`. `status.py` never writes a state.

A book is finished only when translation and alignment are both `done`.
Machine-produced Spanish or alignment stays `draft`.

Chapter approval is independent of book completion. A chapter explicitly
approved in Team Desk has human-approved Spanish and canonical reverse links
and may appear on the LPF project website. It does not set either book state
to `done` and does not authorize export to `cgv-data`. On the website,
approved chapters are ordinary LPF; every other chapter is labeled `Solo
borrador`, and the book is labeled `Libro sin terminar` until the separate
named-human book approval is complete.

For alignment, unit-level `method: hand` is not enough. Every link must also
carry a human-confirmed link status (`hand`, `manual`, or `manual-realign`).
Statuses such as `seeded-hand`, `seeded-auto`, or `seeded-ai` are unfinished
and block `ready`, approval, commit, and export.

If a `ready` file fails the checks, `verify.py` returns it to `draft`.
If a `done` file changes, clear that signature yourself. It returns to `draft`.

## Translator application

`apps/translator/` may exist as an editor. It must read and write the
canonical homes above. It must not keep `translations/`, canonical
alignment, or approval records of its own.

Translator may update only the selected book's approval fields in `STATUS.md`
when a human explicitly presses the stage approval control, enters their name,
and confirms personal review. The selected stage must already be `ready`, and
the canonical status check must pass. Translator must never infer approval,
reuse an investigation approval, or approve in response to AI or verification.

After both approvals, Translator may create one selected-book source commit
only when the human opens **Review & Commit**, reviews the exact file list and
explicitly confirms the commit. The app must run the canonical status check,
refuse an already-populated Git index, and stage only the selected translation,
the selected alignment directory, and that book's row from `STATUS.md`. It must
not commit automatically or include another book's pending ledger changes.

## Publication

```text
Biblia-LBF → validate → review and commit → export → publisher PR → cgv-data
```

Two tools, in order. `tools/export.py` writes the finished-book package.
`tools/publish.py` is the canonical validated publisher: it is the only
sanctioned writer of LBF data into `cgv-data`. Both translation and alignment
must be `done`; chapters and unfinished books never enter `cgv-data`.

| Data | Path in `cgv-data` |
| --- | --- |
| Consumer text | `bibles/LBF/{book}.lbf.md` |
| Consumer alignment | `bibles/LBF/alignments/{book}.alignment.json` |

Those two historical technical paths are the entire published surface for a
book. A publisher commit contains nothing else.

`publish.py` commits in a temporary `git worktree` cut from `origin/{base}`.
It does not switch the caller's branch and cannot carry unrelated working-tree
changes into the commit. It does not push unless asked.

Translator may invoke these same two tools as its final human-triggered steps.
It must require explicit confirmation before invoking `publish.py`, must never
pass `--push`, and must stop after displaying the local publisher branch,
commit, and pull-request link emitted by the canonical publisher.
Translator must label that result **publisher branch prepared**, not
**published**. Finished-book publication is complete when the two canonical LBF paths on
`cgv-data/main` already carry this book's finished content: either the
package `sourceCommit`, or an earlier publish whose translation and alignment
files are unchanged at `HEAD`. A later re-export or leftover publisher branch
must not reopen the create-branch step.

A published `sourceCommit` must name a commit that contains the work it
claims. The book's translation, alignment, and `STATUS.md` row must be
committed before a package is written, and the package must still match `HEAD`
when it is published.

Both tools enforce this. `export.py` refuses to write a package from an
uncommitted tree; `publish.py` checks again before it commits. An export
taken from an uncommitted tree is not publishable: the provenance it records
cannot be resolved by anyone who fetches the repository.

The destination must be a real `cgv-data` checkout — commits present, `origin`
pointing at `cgv-data`. An empty `git init` of the same name is not a
destination.

This repository never imports LBF text or alignment back from `cgv-data`.
It never publishes by copying into a checked-out `cgv-data` working tree.

## LPF website

The project website is built directly from this repository by
`.github/workflows/pages.yml`; it does not consume `cgv-data`. The site may
show the latest committed work before a book is finished. Its generated state
uses `lpf-website-progress-v1` and validates chapter approval against current
Team Desk manifests, approved verse artifacts, canonical Spanish, and
canonical human-confirmed alignment. Approved chapters carry no chapter badge;
all other chapters carry `Solo borrador`. An unfinished book always carries
`Libro sin terminar`.

## Prohibited

- A second editable copy of the same verse or alignment
- Automatic import from another repository
- Silent retention of `done` after the bound text or alignment changes
- Inferred, automatic, anonymous, or pre-verification approval
- Machine zip, gloss DP, or auto-zip presented as finished alignment
- MT verse labels
- Direct mutation of `cgv-data`
- Publishing an export whose `sourceCommit` does not contain the bound work
- Any writer of `bibles/LBF/` other than `tools/publish.py`
- Reader, Observer, or Compiler application code in this repository
- Translation, audit, or alignment evidence outside `SOURCE_POLICY.md`
- Silently completing a verse from model memory when its packet is insufficient
