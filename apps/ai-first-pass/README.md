# LPF AI First Pass

A local, source-first Ollama batch drafter for all 66 LPF books.

It reads the repository-owned sources and writes only the canonical Spanish
files under `translation/`. It never creates alignment, replaces an existing
verse, approves work, commits, exports, or publishes. Every machine-produced
book remains `draft` until it has received complete human review through the
normal LBF workflow.

## Run

1. Install and start [Ollama](https://ollama.com/).
2. Install at least one model, for example `ollama pull gemma3:12b`.
3. Start this app:

   ```sh
   cd apps/ai-first-pass
   npm start
   ```

4. Open <http://127.0.0.1:1430/>.

The app discovers the models installed in Ollama and lets you choose one.
Select all missing books to fill only canonical verse gaps. Stop is safe: the
current Ollama request finishes, completed verses remain saved, and starting
again resumes from the next missing verse.

## Data and status behavior

- NT source: accented Scrivener 1894 TR, with Robinson morphology as evidence.
- OT source: OSHB/WLC direct word stream, mapped to Protestant working labels.
- Existing verse text is immutable to this app.
- `ready` and `done` books are protected.
- A new machine-produced book is recorded as `draft` only through the canonical
  `tools/verify.py <book>` command while the book is incomplete.
- The verifier is not run at completion, so AI output is never promoted to
  `ready` automatically.
- OSHB/WLC has no source text for the canonical LBF label Nehemiah 7:68. The app
  exposes that one source gap and refuses to invent a translation for it.

Set `LBF_OLLAMA_BASE_URL` if Ollama is not listening at
`http://127.0.0.1:11434`.
