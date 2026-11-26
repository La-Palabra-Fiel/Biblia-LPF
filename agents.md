Read `DATA_CONTRACT.md` and `WORKFLOW.md` before changing translation,
alignment, status, import, export, or dataset-loading code.

If a request conflicts with `DATA_CONTRACT.md`, stop and explain the conflict.
Do not work around it.

This repository is the only editable source of truth for LBF.
Work only here. Do not open or write `cgv-reader`. `cgv-data` is output only.

Never import LBF text or alignment automatically from another repository.
Never move, copy, regenerate, synchronize, or delete canonical data unless
the task names the source repository, destination repository, migration
phase, and validation procedure.

When two copies differ, stop. Do not choose by timestamp, file size,
apparent completeness, or Git history alone.

Spanish lives in `translation/`. Alignment lives in `alignment/`.
Translation is produced by `tools/pipeline/`: Cursor Auto drafts and audits;
Sonnet steps in only when a verse is questionable. The unattended chapter
command is `python3 tools/pipeline/auto_pass.py <book> <chapter>`. It calls
the Cursor CLI. A person reads and approves when that command has finished.
Do not use GPT or Grok unless the task explicitly asks for the paid path.
`STATUS.md` and `tools/verify.py` do not decide the Spanish. States recorded
there are `none` | `draft` | `ready` | `done`. Never infer `done`.
Translator may record `done` only after the user explicitly activates its
named-human approval control for a stage already marked `ready`.

Never use MT numbering. Always Protestant.
Never run machine zip, gloss DP, or whole-book auto-align.
Never present auto-zip or gloss as finished alignment.

Never preserve `done` after changing the bound translation or alignment.
Never publish directly into a checked-out `cgv-data` working tree.
Export only through the canonical validated publisher.

The publisher is two scripts and nothing else:
`python3 tools/export.py <book>` writes the package to `/tmp/lbf-export/`.
`python3 tools/publish.py <book> --data-repo <path>` commits it to a
`lbf-<book>-<date>` branch in `cgv-data`. Never `git add` LBF text or
alignment into `cgv-data` by hand. Never `cp` into `bibles/LBF/`.

Source IDs that differ from established consumer IDs are declared only in
`tools/consumer_books.json`. Export, publish, and Translator must use that
shared mapping; never rename a generated package or a `cgv-data` artifact by
hand. The publisher's alias-cleanup option is only for an explicitly named
corrective migration and must validate the complete generated alias pair
before removal.

`export.py` refuses if the bound source is not committed. The fix is a commit
by the user, either directly or through Translator's explicit **Review &
Commit** confirmation; never a flag or blind re-run.

`publish.py` does not push unless given `--push`. Do not pass `--push` for
the user. Do not open the pull request for the user. Print the branch and
stop.

Do not defeat an `export.py` or `publish.py` refusal. They refuse because
the signature, the commit, or the package does not bind the work. Fix the
cause. Never commit Biblia-LBF on the user's behalf to clear one. Translator
may create the selected-book commit only when the user reviews its exact file
list and explicitly presses its commit confirmation; that action is the user's
commit and must never be automatic.

## Imported Claude Cowork project instructions
