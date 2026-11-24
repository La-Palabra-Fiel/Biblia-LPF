# TR1894–MACULA attachment contract

## Status and purpose

This document governs every attempt to use MACULA syntax with the TR1894 New Testament.

**TR1894 is the immutable textual authority. MACULA is an advisory structural witness that may attach to TR1894.**

The direction is always:

> TR1894 token or span ← MACULA structural attachment

It is never:

> MACULA token or tree ← altered TR1894 text

This contract applies to experiments, proposals, translation-stage tooling, review artifacts, exports, and published datasets.

## 1. Authority

1. TR1894 supplies the authoritative Greek token identities, token order, token surfaces, and verse boundaries.
2. MACULA supplies advisory syntax only: grouping, dependency, clause, role, and related structural information.
3. A MACULA terminal is evidence for an attachment. It never becomes the identity of a TR1894 token.
4. No process may insert, remove, replace, rename, reorder, merge, or split TR1894 tokens to make them resemble MACULA.
5. A difference between TR1894 and MACULA must remain visible as a difference. It must not be silently normalized away.

## 2. Required data model

Every durable record must begin with one or more TR1894 token IDs or an explicitly bounded TR1894 span.

An attachment record must state:

- the TR1894 token ID or ordered TR1894 span;
- the MACULA node or terminal IDs used as evidence;
- the structural claim being attached;
- the attachment method;
- any textual difference between TR1894 and MACULA;
- whether any MACULA terminals were left unused;
- whether any TR1894 tokens received no MACULA syntax;
- proposal, review, and approval status;
- provenance sufficient to reproduce the result from pinned inputs.

The attachment method must be one of these explicit classes:

1. **Exact attachment** — compatible TR1894 and MACULA terminals support the structural attachment directly.
2. **Adapted attachment** — MACULA structure remains applicable, but its terminals differ from TR1894. The structural claim is attached to native TR1894 tokens, and the difference is recorded.
3. **TR-native reviewed structure** — MACULA cannot supply the required structure. A human-reviewed structure is stated over TR1894 tokens without pretending it came from MACULA.
4. **No MACULA syntax** — the TR1894 token or span remains present and ordered, but no defensible MACULA structural claim is attached.

There is no fifth state in which TR1894 is modified to preserve a MACULA tree.

## 3. Processing order

The translation process must use this order:

1. Establish the authoritative TR1894 tokens and token IDs.
2. Complete or load the translation alignment against those TR1894 tokens.
3. Attempt to attach MACULA structure to those existing TR1894 tokens and spans.
4. Record exact attachments, adapted attachments, and unresolved differences explicitly.
5. Send non-exact structural claims to review.
6. Validate the complete TR1894 passage independently.
7. Publish only data that has passed the required approval and release gates.

MACULA attachment is therefore a translation-stage enrichment step. It is not a reconstruction of the TR1894 text.

## 4. Validation requirements

A passage may pass mechanical validation only when all of the following are true:

- every TR1894 token in scope appears exactly once in authoritative TR order;
- no TR1894 token surface or identity has changed;
- every structural attachment points from a TR1894 token or span to its MACULA evidence;
- every MACULA terminal used as evidence is accounted for without becoming a TR token identity;
- every unused MACULA terminal is reported;
- every TR1894 token without defensible MACULA syntax is reported as **No MACULA syntax**;
- all adapted and TR-native structures include an explicit reason and provenance;
- the result can be regenerated from the saved proposal and its pinned source inputs;
- regeneration produces no unexplained or unclassified token.

A mechanical pass proves only that the artifact is complete and reproducible. It does not prove that its linguistic analysis is correct.

## 5. Review and verification

1. The author of an attachment proposal may not verify that proposal.
2. An independent verifier must examine both witnesses:
   - the mechanical report; and
   - the Greek reading and structural claim.
3. The verifier returns **VERIFIED** or **FAILED**, with references and reasons.
4. Script success alone is not approval.
5. AI completion alone is not approval.
6. Only a named human may approve a non-exact structural decision for canonical use.

## 6. Publication boundary

1. Proposals and generated candidates are noncanonical and must not be published.
2. The Reader, Observer, and Compiler are read-only consumers. They must not create or repair these attachments.
3. Approved attachment data may enter the publication process only through the established LaPalabraFiel export and release gates.
4. A published dataset must preserve the distinction between:
   - MACULA-derived syntax;
   - adapted MACULA syntax;
   - human-reviewed TR-native syntax; and
   - no MACULA syntax.
5. The user interface must present MACULA-derived information as advisory help, not as the authoritative wording of TR1894.

## 7. Current Romans 11 practice boundary

Romans 11:11–36 is the only authorized practice scope for developing this attachment model.

The file `nt-syntax/proposals/RO.11.11-36.macula.proposal.json` uses the TR1894-first attachment model defined here. It remains a noncanonical proposal: its mechanical result must not be treated as human approval or permission to publish.

Work outside Romans 11:11–36 requires separate explicit authorization.

## 8. Stop conditions

Stop the process rather than guessing when:

- it is unclear which TR1894 token or span owns an attachment;
- the proposed structure would require changing TR1894;
- the MACULA evidence does not support the claimed structure;
- a textual difference is being hidden rather than recorded;
- the artifact cannot be regenerated from pinned inputs;
- the author is being asked to verify the author's own claim; or
- publication is requested before approval and release gates are satisfied.

These are contract failures, not inconveniences to work around.
