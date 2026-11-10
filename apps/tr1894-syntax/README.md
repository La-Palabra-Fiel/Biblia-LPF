# TR1894 Syntax Review

> **Legacy investigation only — not the authorized NT workflow.** This app
> reads SBLGNT and the superseded `tr1894.txt` token layer. Do not use its
> projections as LPF syntax. The authorized gate is
> `tools/build_nt_macula_mapping.py`, based on SCV-authoritative tokens,
> Robinson morphology, and pinned MACULA Greek Nestle1904 structure-only data.

A local browser app for a bounded, review-first TR1894 syntax-fixture workflow. It projects the completed MACULA Greek SBLGNT clause trees onto local TR1894 terminals, then defaults to `qwen2.5:14b` for help with the remaining decisions.

It is deliberately suggestion-only:

- Reads the immutable NT terminal spine from `source/greek/TR1894/tr1894.txt`.
- Reads MACULA Greek SBLGNT `nodes` only as a comparison source. By default it uses `/Users/johnwry/Downloads/macula-greek-main`; set `LBF_MACULA_GREEK_ROOT` to select another local checkout.
- Aligns source-normalized terminals per verse, projects the nested SBLGNT clause/phrase structure onto matching TR terminals, and explicitly lists SBL-only and TR-only readings.
- Displays Robinson morphology as helper evidence without replacing the TR text.
- Asks Ollama for a structured clause-plan suggestion, not a finished analysis.
- Places a reference-projected JSON review draft in the editor and runs the canonical prototype validator against a temporary file.
- Never saves fixtures, changes translation/alignment/status, approves work, commits, exports, or publishes.

## Start

Start Ollama and install the default model if necessary:

```sh
ollama pull qwen2.5:14b
cd apps/tr1894-syntax
npm start
```

Open <http://127.0.0.1:1431/>. Set `LBF_OLLAMA_BASE_URL` if Ollama is running elsewhere.

## Review workflow

1. Load the required Matthew passage and read the TR terminals.
2. Build a reference-projected draft from the local SBLGNT tree.
3. Resolve every listed SBL/TR difference, clause boundary, attachment, and UTR-only morphology position yourself.
4. Use Ollama only for a reviewable suggestion about the unresolved decisions.
5. Run the checks, then use the normal repository process to make a manual fixture change.

The app does not provide a save button by design: neither the SBLGNT projection nor a model response is a corpus decision.
