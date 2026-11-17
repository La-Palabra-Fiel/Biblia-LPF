# Documentary Koine research sources

Status: authorized for named-human lexical research and documented `HOLD`
adjudication. These datasets are not authorized for automatic model packets
and cannot alter translation or alignment without a recorded human decision.

## Primary corpus selected for verification

The authorized primary research corpus is the `DDbDP/` component of Papyri.info
`papyri/idp.data`, maintained by the Duke Collaboratory for Classics Computing.
The upstream repository states that its data is CC BY 3.0 with copyright and
attribution to the respective constituent projects.

Evaluation pin recorded on 2026-11-11:

- repository: `https://github.com/papyri/idp.data`;
- commit: `56f68ee627b3602acd3ec9e0eee411d5912a9e3a`;
- commit date: `2026-11-11T19:08:15Z`;
- intended component: `DDbDP/` Greek documentary transcriptions only;
- status: the controlled candidate set and a normalized full-DDbDP concordance
  have been verified; no upstream corpus snapshot has been admitted to the
  repository and the source is not authorized for canonical packets.

Translations, DCLP literary texts, APIS images and unrelated constituent
collections are outside the authorized allowlist.

## Discovery corpus

`alekkeersmaekers/duke-nlp` is an automatically annotated snapshot of DDbDP
used by Trismegistos Words. Its README reports approximately 99 percent lemma
accuracy and 95 percent morphology accuracy, but the source DDbDP snapshot is
from September 2016. LPF therefore uses it only to discover candidates.

The exact evaluation pin, archive hash, file hashes, allowed research fields
and rejected automatic fields are recorded in
[`DUKE_NLP_MANIFEST.json`](DUKE_NLP_MANIFEST.json).

No upstream XML is committed here. The evaluated archive was downloaded to a
temporary directory and its expanded files were checked against the manifest.
Anyone repeating the research must acquire the pinned archive, verify its
SHA-256 and then validate every expanded XML file before searching it.

## Controlled primary cross-check

The primary cross-check manifest is
[`DDbDP_QUERY_MANIFEST.json`](DDbDP_QUERY_MANIFEST.json). It binds:

- two literal searches at the pinned DDbDP commit;
- their 67-path union;
- three additional records whose target forms cross EpiDoc markup and were
  recovered from the pinned discovery corpus;
- 70 DDbDP transcription XML files and 85 paired HGV metadata XML files by
  count and aggregate SHA-256.

The upstream XML remains in a temporary evaluation cache and is not committed.
`tools/research/ddbdp_primary_inventory.py` validates the aggregate hashes,
selects the canonical branches of EpiDoc alternatives, preserves supplied and
unclear letters, joins only line breaks explicitly marked `break="no"`, and
reports dates conservatively. A one-sided date is never promoted to an exact
first-century occurrence.

Literal GitHub search does not cross XML elements or line breaks, so the
cross-check was followed by a full normalized scan of a clean sparse checkout
at the pinned commit. The checked-out Git trees were:

- `DDbDP/`: `d39ff5831b5ba7efbf316c600af4c6b340701585`, 67,981 XML;
- `HGV_meta_EpiDoc/`: `aa2a956bf9bb292cea1c6c3e55da56494c8fc451`,
  68,023 XML.

The scan found 57 target-prefix surfaces and paired every occurrence with HGV
metadata. Its JSON result has SHA-256
`9ef14fd937400de38dcb95eebd547eee3f59ba8dfd1e5293c07dc4305977ff13`
and is stored at
[`inventories/metano-family.json`](inventories/metano-family.json). The result
is derived and can be regenerated; the 926 MB temporary checkout is not
committed to Biblia-LBF.

No occurrence is dated within a closed interval wholly inside 1–100 CE. Three
documents have a one-sided date range that can mathematically include that
period, so the scan supports a negative search report but not proof of lexical
absence in the first century.

## Authorization boundary

The human authorization recorded on 2026-11-11 permits the pinned DDbDP Greek
transcription and paired HGV metadata in lexical dossiers and documented human
adjudication. The automatically annotated `duke-nlp` snapshot remains a
discovery index only. Neither source is currently exposed to a translation or
alignment model; doing so requires a new packet-policy identifier, an
allowlist loader, leakage tests, and an explicit packet migration.

Every consultation is announced to the user and recorded in
[`CONSULTATIONS.json`](CONSULTATIONS.json). The log distinguishes evidence
gathering from human adjudication and records whether a model received the
documentary evidence.

## Required verification chain

An annotated hit is not evidence by itself:

```text
duke-nlp lemma candidate
        → current pinned DDbDP transcription
        → document date, provenance and genre
        → editorial restoration and immediate context
        → human classification in a lexical dossier
```

The primary transcription, not the automatic lemma, is the evidence. An
occurrence containing editorial restoration is marked as such. Absence from
the discovery corpus is reported as a negative search result, never as proof
that the word did not exist.

## Date bands

- exact first century: `period_min = 1` and `period_max = 1`;
- overlaps first century: the date range contains century 1 but is broader;
- near contemporary: 100 BCE through 200 CE, labeled by its actual range;
- diachronic comparison: everything outside that window.

Only the first category may be called an exact first-century occurrence.

## Known limitations

- Documentary papyri are geographically concentrated in Egypt.
- Documentary survival is uneven by genre, place and century.
- An automatic lemma can be wrong even when its reported aggregate accuracy is
  high.
- Editorially restored letters are not equivalent to fully preserved forms.
- A missing result cannot establish semantic impossibility.
- Documentary usage supplements but never overrides the canonical TR1894
  surface, morphology, syntax or discourse of an LPF verse.

