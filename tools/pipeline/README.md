# Translation pipeline

## Blind model comparison

`compare_draft_models.py` compares GPT-5.6 Sol and GPT-6.1 Sol on twelve
approved Exodus verses without exposing the approved answer to either model.
It is noncanonical, writes only under `/tmp`, and never changes translation,
alignment, status, or Team Desk candidates.

Prepare the bound sample and display the paid-call ceiling:

```bash
python3 tools/pipeline/compare_draft_models.py prepare
```

`prepare` makes no API calls. The paid phase requires the person to copy the
displayed `maximumUsd` explicitly and refuses if a packet, approval, prompt,
sample, or price assumption changed:

```bash
python3 tools/pipeline/compare_draft_models.py run --confirm-max-usd <maximumUsd>
```

Automatic results are written to `report.json`; anonymous candidates and the
human review fields are written to `blind-review.json`. Neither file approves
Spanish or alignment.

`SOURCE_POLICY.md` is the closed, normative source boundary. Any model-facing
packet must bind `lbf-source-policy-v4`; mismatched packets are refused. No
other Bible, lexicon, syntax tree, web lookup, retrieval source, or existing
LBF Spanish may enter drafting or fidelity decisions.

The closed OT packet now includes the authoritative OSHB/WLC surface and
morphology, the allowlisted structural subset of pinned MACULA Hebrew,
adjacent original-language context, deterministic same-lemma OSHB corpus
usage, and pinned Open Scriptures HebrewLexicon possibilities. Raw MACULA
glosses, translations, LXX/Greek fields, SDBH material, semantic domains,
frames, and sense selections are rejected.

Validate the engineering and cross-genre evidence pilots without model calls:

```sh
python3 tools/pipeline/validate_ot_evidence.py --exodus-1 --stress
```

Prepare one canonical GPT request per verse, also without model calls:

```sh
python3 tools/pipeline/prepare_gpt_chapter.py exodo 1 --label gpt-pilot
```

Draft and independently audit one verse through the authorized GPT path:

```sh
python3 tools/pipeline/draft_gpt.py exodo 1 1 --label gpt-pilot
python3 tools/pipeline/audit_gpt.py exodo 1 1 \
  --candidate-file pipeline/ot/exodo/exodo-1-1.draft-gpt-pilot.json
python3 tools/pipeline/spanish_check_gpt.py exodo 1 1 \
  --candidate-file pipeline/ot/exodo/exodo-1-1.draft-gpt-pilot.json
```

These are separate gates: the audit checks source fidelity; the Spanish check
checks current Latin American grammar, idiom, and oral readability. A source
audit pass cannot override a Spanish-check failure. Any draft uncertainty,
added concept, dropped uncited unit, audit finding, or Spanish-check finding
parks the verse for human adjudication.

A cited mechanical or Spanish-flow failure may receive one bounded repair:

```sh
python3 tools/pipeline/revise_gpt.py exodo 1 1 \
  --candidate-file pipeline/ot/exodo/exodo-1-1.draft-gpt-pilot.json \
  --findings-file pipeline/ot/exodo/exodo-1-1.audit-gpt-gpt-pilot.json \
  --label gpt-pilot-repair
```

The repaired candidate must repeat both independent gates. A repair never
adjudicates an unresolved lexical or syntactic uncertainty.

Without `OPENAI_API_KEY`, these commands preserve request JSON for the
authorized GPT task. They never write translation Markdown, alignment, or
`STATUS.md`.

The user has authorized a GPT-6.1 Sol path. Its governing chapter workflow is
documented in `WORKFLOW.md`. The Cursor command later in this file is the
retained legacy implementation and must not be represented as the GPT path.

Team Desk performs a no-cost deterministic preflight before a named human can
approve a verse. It checks complete packet-token coverage, known token IDs,
alignment precision, Spanish-unit reconstruction, and identical supplied-word
italics. This preflight never calls a model. Existing human approvals are
grandfathered while their Spanish still matches the canonical verse; packet
fingerprint drift alone does not purchase another draft or force retrospective
chapter approval.

Spanish mood checks must be tied to their source. The established **vivirá**
check belongs to the qal sequential perfect in Exodus 1:16; it is not a global
ban on **que viva**. Psalm 119:17 has first-person cohortatives and allows
**para que viva y guarde**. Team Desk recomputes existing deterministic lint
results with current rules without rewriting historical artifacts or clearing
independent fidelity-audit findings.

New Team Desk screening drafts use GPT-6.1 Sol at low reasoning with a
4,000-token completion ceiling and one best-ranked corpus parallel per lemma.
The model choice is scheduled for human review beginning 2026-11-30; the date
does not change it automatically. Existing compatible GPT-5.6 Sol candidates
at low or medium reasoning are reused without another paid call. The displayed
maximum is sent back with the confirmation; if the estimate changes, the
server refuses to start and asks for a new confirmation.

The named whole-chapter approval records every unchanged candidate that passes
all deterministic gates and has no uncertainty or failed required audit. It
does not approve HOLD verses. Those remain the only cards requiring individual
work, and the chapter manifest is withheld until they are resolved.

This is the procedure. One Protestant verse at a time, from a source
packet. NT: **TR1894**. OT: the canonical evidence bundle described above.

Cursor Auto drafts and audits. GPT-5.6 Terra steps in only when the verse is
questionable. Grok is not in this procedure. `STATUS.md` and
`tools/verify.py` do not accept a verse.

Spanish is current Latin American (`tú` / ustedes), not Spain
*vosotros*. Proper names: `translation/PROPER_NAMES.md`.
יהוה → Yahvé. אלהים as God → Dios.

## Stations

| Order | Who | When |
| --- | --- | --- |
| 1 | source packet | every verse |
| 2 | Cursor Auto drafts | every verse |
| 3 | local lint | every verse, no model |
| 4 | Cursor Auto audits | lint passed |
| 5 | GPT-5.6 Terra | the verse is questionable |
| 6 | Cursor Auto audits again | only the Spanish Terra wrote |
| 7 | Cursor Auto checks the Spanish | every verse, before and after Terra |

A clean pass stays with Auto. Clean means the audit has no fail or warn,
the Spanish grammar and flow check passes, and the draft has no uncertainty,
added concept, or dropped unit.

Terra runs when any of these is true:

- lint hits a known failure (*vosotros*, *parir*, dual stones turned
  into a stool, or another rule in `lint_lib.py`)
- the audit fails or warns
- the Spanish is faithful but does not flow naturally
- the draft lists an uncertainty, an added concept, or a dropped unit

After Terra, Auto audits that Spanish once for fidelity to the Hebrew.
Then Auto checks the Spanish itself: every word has to be current
Latin American Spanish a reader can say. A word the fidelity audit
accepts, such as an archaic interjection, still fails this check. The
verse is parked. The check does not rewrite the verse: a new candidate
that fails is not written, and a bad line already in the file stays for
the translator. The check is saved as
`{book}-{chapter}-{verse}.spanish-check.json`. A fidelity `pass` is
written into the verse only after that check passes. Warns on the
fidelity pass stay in the audit file for the human read. Terra does
not run again.

A word the Hebrew does not have, added so the Spanish can be a sentence,
is italic: *son*. A marked copula does not park the verse. When a warn
is only number — a singular head noun against a plural participle —
Terra chooses the grammatical Spanish and writes the choice in
`readerNote` on the chapter report. A clause-role problem — who acts, or
which noun a preposition governs — stays on hold. Terra does not repair
it. That verse is for the translator, one verse at a time.

## Run a chapter

```sh
python3 tools/pipeline/auto_pass.py exodo 1
python3 tools/pipeline/auto_pass.py exodo 1 --from 1 --to 5
```

This command calls the Cursor CLI (`agent`) for Cursor Auto and, when
the verse is questionable, for Terra. It walks the chapter and writes
a passing repair into `translation/`. When it finishes, a person reads
the chapter and the report and approves. It does not sign `STATUS.md`.

`agent` has to be on `PATH` and logged in:

```sh
curl https://cursor.com/install -fsS | bash
agent login
agent models
```

`LBF_CURSOR_AUTO_MODEL` defaults to `auto`. `LBF_CURSOR_POLISH_MODEL`
defaults to `gpt-5.6-terra`. The former Sonnet variables remain fallback
overrides for compatibility.
If the CLI rejects the id, set one from `agent models`.

Spanish already in the book file is audited. A clean pass stays. A fail
or a warn goes to Terra once. Auto audits that Spanish again. Verdict
`pass` replaces the verse. Verdict `fail`, or a lint hit that remains,
parks the verse and leaves the previous line.

The report is
`pipeline/{ot|nt}/{book}/_logs/{book}-{chapter}.auto-pass.json`.

A verse with no Spanish yet is drafted by Auto, then audited on the
same path. It enters the book file when the audit accepts it.

`--no-resume` calls the models again. `--full` sends every verse to
Terra, including a clean pass. Leave both off for a normal chapter.

## Continue through the Old Testament

Use the OT runner to avoid typing the next book and chapter by hand. It runs
`auto_pass.py` sequentially and stops on errors:

```sh
git pull --ff-only
python3 tools/pipeline/auto_ot.py --from-book exodo --from-chapter 21
```

To redo all existing OT wording through GPT-5.6 Terra, including verses whose
older fidelity audit passed, start at Genesis with full mode:

```sh
python3 tools/pipeline/auto_ot.py --from-book genesis --from-chapter 1 --full
```

Full mode does not blindly accept a rewrite. Each Terra candidate must still
pass the independent source-fidelity audit and the Spanish-flow check before
it can replace the existing verse. No human approval state is recorded.

Pull once before the pipeline starts, and only when the working tree permits
it. Do not pull between chapters: the pipeline may have changed the tracked
translation file. The runner does not commit, sign `STATUS.md`, align, or
publish. When it finishes, a person must review the chapters and reports
before recording any human approval.

The OT runner processes six independent verses concurrently by default.
Each verse still follows the same Auto → lint → Spanish check → conditional
Terra → Auto re-audit → Spanish check sequence, and translation-file writes
are serialized.
Use `--workers 1` for the original serial behavior or a smaller value if the
Cursor service throttles concurrent calls. Cursor calls retry transient
timeouts, network failures, empty answers, and malformed JSON twice by default.
The controls are `LBF_CURSOR_TIMEOUT`, `LBF_CURSOR_RETRIES`, and
`LBF_CURSOR_RETRY_DELAY`.

A chapter that still has errors after its call retries is queued instead of
stopping the OT run. After the first pass, the runner revisits incomplete
chapters for two retry rounds. Change that with `--retry-rounds`; unresolved
chapters remain errors and make the final command exit nonzero.

The request queue is still there for answering inside the editor, one
JSON file at a time:

```sh
python3 tools/pipeline/run_chapter.py exodo 1
python3 tools/pipeline/run_book.py exodo
```

Those scripts write requests under `pipeline/`. They do not call the
CLI. Re-run them after each reply file exists. `finish_book_apply.py`
copies that queue's `passed` verses into the book file.
`auto_pass.py` is the command that finishes a chapter on its own.

## Answer the queue

The chapter queue is `pipeline/{ot|nt}/{book}/{book}-{chapter}.queue.json`.
Read `waiting`. Each item has `verse`, `stage`, `model`, `request`, and
`reply`.

| `model` | Who answers |
| --- | --- |
| `cursor-auto` | Cursor Auto |
| `sonnet` | Sonnet |

Open the request JSON. Follow `system` and `user`. Write only the JSON
object to the reply path. Do not write `translation/` or `STATUS.md`.

Requests and replies use these names:

| Stage | Request | Reply | Saved result |
| --- | --- | --- | --- |
| packet | | | `{book}-{chapter}-{verse}.packet.json` |
| draft | `…draft-auto.request.json` | `…draft-auto.reply.json` | `…draft-auto.json` |
| lint | | | `…lint.json` |
| audit | `…audit-auto.request.json` | `…audit-auto.reply.json` | `…audit-auto.json` |
| Sonnet | `…polish-sonnet5.request.json` | `…polish-sonnet5.reply.json` | `…polish-sonnet5.json` |
| re-audit | `…audit-pulir.request.json` | `…audit-pulir.reply.json` | `…audit-pulir.json` |

The verse moves like this:

1. Draft request. Auto replies. Re-run.
2. Lint. A lint failure skips the audit and asks Sonnet next.
3. Otherwise an audit request. Auto replies. Re-run.
4. Clean pass: the queue marks the verse `passed`.
5. Questionable: a Sonnet request. Sonnet replies. Re-run.
6. Re-audit request. Auto replies. Re-run.
7. Re-audit `pass`: `passed`, even when warns remain. Re-audit `fail`: `hold`.

Repeat until `waiting` is empty. `--no-resume` redoes verses that
already passed or are parked. Leave it off for a normal run.

`--full` asks Sonnet for every verse, including clean passes. Do not
use it for a normal chapter.

## Put passed Spanish in the book file

```sh
python3 tools/pipeline/finish_book_apply.py exodo
```

This copies `passed` verses into `translation/ot/exodo.md` or
`translation/nt/{book}.md`. Sonnet’s text is used when Sonnet ran;
otherwise the Auto draft. Holds are written to
`pipeline/{ot|nt}/{book}/_logs/parked-holds.json`. The script does not
sign `STATUS.md`.

Book file shape:

```markdown
# Tito

## Capítulo 1

### 1:1

Pablo, siervo de Dios…
```

One verse, one `### chapter:verse` heading. One file per book.

## Spanish already in translation/

```sh
python3 tools/pipeline/auto_pass.py exodo 1
```

That command audits the file, sends fails and warns to Sonnet once,
re-audits, and writes repairs whose verdict is `pass`.

`audit_translation.py` only writes audit requests for a manual editor
reply. It does not repair. Paid xAI is `audit_translation.py … --xai`
and is not the procedure.

## Previous script

The paid GPT → Grok runner is a different file:

```sh
python3 tools/pipeline/run_chapter-old.py exodo 1
```

That is GPT, then local lint, then Grok. Sonnet runs only when Grok
warns. Its JSON has `passed`, `holds`, and `errors`, and no `engine`
field. `draft_gpt.py`, `audit_grok.py`, and `polish_sonnet.py` belong
to that path. They are not the next step after a Cursor Auto request.

## Checks

```sh
python3 tools/pipeline/test_auto_pass.py
python3 tools/pipeline/test_cursor_auto.py
python3 tools/pipeline/test_source_packet.py
```
