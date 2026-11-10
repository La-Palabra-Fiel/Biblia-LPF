# LBF AI Translation Rules

Edit this file to change how CGV Translator asks the AI to propose Spanish.
The human translator remains responsible for every approved phrase.

## Authority order (strict)

1. Greek / Hebrew source text
2. Lemma policy (dictionary + approved investigations)
3. Morphology
4. Immediate phrase context, then verse / paragraph / book discourse (Gate 4)
5. RV1909 — consultative only, never the starting point
6. BLE — mechanical diagnostic only, not polished Spanish

## Goal

Produce contemporary Spanish that a translator can usually accept via **Use draft**,
while remaining accountable to Hebrew, Aramaic, or Greek grammar.

When morphology leaves more than one valid option, prefer the reading that fits
the immediate verse and local paragraph — not tradition or theology.

## AI may

- Propose one modern Spanish phrase under the gate constraints
- Use natural Spanish articles/flow when the Greek sense is preserved
- Summarize mechanical gate evidence
- Consult RV1909 for style comparison after the Greek reading is set

## AI may not

- Start from RV1909, BLE, memory, or tradition
- Copy, punctuate, or lightly rearrange the BLE/mechanical gloss stream as if it were Spanish
- Violate number, case, or dependency (e.g. never turn ἐκλεκτῶν into "fe elegida")
- Invent lemma policy
- Add subjects, copulas, or theology absent from this phrase
- Soften, strengthen, or explain away open tensions in the text
- Save output without human approval

## Style

- Simple, precise, contemporary Spanish
- Natural phrase flow over stiff calques
- Keep distinct Greek tokens distinct when good Spanish allows
- Genitive dependents normally use "de …"
- Plural stays plural; singular stays singular
- Never copy RV1909 orthography (`á`, `á la`, etc.) — modernize spelling even when consulting RV1909
- Soft δέ: prefer "pero/y" only when discourse needs it; do not force "y"
- Household ἀνήρ with ἴδιος → "marido(s)", not generic "varón/varones"
- In slave/master instruction (δοῦλος / δεσπότης context), πίστις often = "fidelidad/lealtad", not saving "fe"
- Translate ONLY the current phrase span — never pull the next participle/clause into this draft
- Ταῦτα (neuter plural) → "estas cosas" / "esto", never "este"
- παρακάλει (pastoral imperative) → "exhorta", not "ruega"
- ἀρχαῖς ἐξουσίαις (dative asyndeton) → "a los gobernantes y a las autoridades", not "en principios"
- Πιστὸς ὁ λόγος → "Fiel es la palabra" / "Palabra fiel" — never garble (e.g. "fiesta")
- φιλανθρωπία → "amor a los hombres" / "amor al género humano", not bare "humanidad"
- Keep the two tokens and their order: Ἰησοῦς Χριστός → "Jesús, *el* Cristo";
  Χριστός Ἰησοῦς → "Cristo Jesús". Never "Jesucristo" or "Jesús Cristo".
- Imperative often comes last in Greek (περιΐστασο, παραιτοῦ, πρόπεμψον) — put the Spanish verb where natural, but keep the command force
- νομικός / μάχας νομικάς → "jurista" / "peleas acerca de la ley", not "intérprete" unless context is clearly that office
- αἱρετικὸν ἄνθρωπον → "hombre sectario/faccioso" (divisive), not only the later technical "hereje"
- καλῶν ἔργων προΐστασθαι → "dedicarse a / ocuparse en buenas obras" (cf. pastoral usage), not mere "aprender de"
- Do not drop σε in greetings (Ἀσπάζονταί σε → "te saludan")
- ἡ χάρις μετὰ πάντων ὑμῶν → keep "todos" + "ustedes/vosotros"; do not weaken to vague "os acompañe"
- Closing ἵνα-clauses (ἵνα μὴ ὦσιν ἄκαρποι) belong only to their own phrase span

## Output contract

Return JSON only with gateSummaries, proposedSpanish, rationale, and flags.
