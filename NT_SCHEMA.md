# TR1894-Based NT Syntax Schema

Status: proposed specification, 2026-09-09; structural-source policy authorized
2026-11-09. This remains a schema proposal for a small validated prototype,
not an NT corpus build and not a replacement text edition.

The prerequisite TR1894 + Robinson text/morphology layer completed human and
mechanical reconciliation on 2026-11-09: 7,957 Protestant verses and 140,655
SCV-authoritative tokens, all bound to Robinson morphology, with zero `REVIEW`
and zero `HOLD`. This does not complete or authorize the syntax layer.

The MACULA Greek comparison gate requires token-level agreement among SCV,
Robinson, and the pinned Nestle1904 lowfat terminal before MACULA structure can
use an anchor. A human-approved SCV/Robinson spelling difference or token merge
remains valid morphology evidence but cannot anchor MACULA structure. Current
counts are generated in `MACULA_GREEK_MANIFEST.json`; unresolved differences
are not syntax decisions. A review-only Filipenses 1 candidate demonstrates
minimal branch isolation; it is not canonical syntax.

## Design commitments

1. TR1894 is the only NT text authority. Every terminal is reconstructible from a pinned TR source record.
2. Morphology is bound to TR tokens but is a separate layer. A morphology provider never changes a TR surface or token order.
3. Syntax is a proper rooted tree of stable nodes. Lowfat and TSV are deterministic projections, not alternative sources of truth.
4. Clause decisions have evidence and a decision status. The pinned MACULA
   Greek source authorized by `SOURCE_POLICY.md` is structure-only comparison
   evidence; its Greek readings and semantic annotations are never canonical.
5. Semantic roles, referents, senses, and discourse annotations are deferred until syntax is stable.

## Canonical document

One proposed canonical document per book:

```text
nt-syntax/
  MAT.syntax.json
  ...
```

This is a new research-dataset area, separate from `translation/`, `alignment/`, and `STATUS.md`. It does not alter canonical LBF verses or alignment. Its formal structure is `schema/tr1894-syntax.schema.json`.

```text
document
├── provenance
├── tokens[]              # TR text and morphology layer
├── sentences[]           # sentence metadata/root references
├── nodes[]               # canonical syntax tree
├── clauses[]             # query-oriented derived index
└── reference_links[]     # optional MACULA/treebank comparison only
```

## Identity conventions

| Entity | Convention | Example |
| --- | --- | --- |
| Token | `BOOK.chapter.verse.wNNN` | `MAT.1.1.w001` |
| Sentence | `BOOK.chapter.sNNN` | `MAT.1.s001` |
| Syntax node | `<sentence-id>.nNNN` | `MAT.1.s001.n003` |
| Clause | `<sentence-id>.cNNN` | `MAT.1.s002.c004` |
| Phrase | `<sentence-id>.pNNN` | `MAT.1.s002.p011` |

Numbers are source order within the containing verse/sentence. They are never reused after a source-tokenization change. The document provenance declares source revision and tokenization-policy version, so an ID is never presented as edition-independent.

## Layers

### Text and morphology: `tokens[]`

Each token has a stable TR `token_id`, exact UTR beta-code surface, optional
deterministic Unicode display, reference, ordinal, and source locator. The
Robinson morphology object preserves the provider's raw tag and Strong's
identifiers and may later expose normalized features: part of speech, case,
number, gender, person, tense, voice, mood, and lemma. Null/absent means
unavailable, never guessed. The corresponding whole-verse SCV comparison must
be `exact`; otherwise the verse remains `HOLD` and cannot enter syntax
projection.

### Canonical syntax: `nodes[]`

Each node has one stable `node_id`, a `kind`, ordered `children`, and exactly one parent except the sentence root. A terminal node has one `token_id` and no children. A non-terminal has child IDs. Fields are:

* `kind`: `sentence`, `clause`, `phrase`, `coordination`, or `word`.
* `category`: language-appropriate category, e.g. `cl`, `np`, `pp`, `vp`, `advp`.
* `function`: optional relation such as `s`, `v`, `o`, `io`, `p`, `adv`, `vc`, `oc`.
* `rule`: observed structural rule, if assigned.
* `head`: optional child node ID, never a bare source position.
* `clause_type`: controlled label such as `verbal`, `verbless`, `coordinate`, `relative`, `subordinate`, or `reported-speech`.
* `evidence`: source-token IDs and a human-readable decision note.

`category`, `function`, and `clause_type` are separate. A Greek relative construction can have a language-specific clause type and phrase function without forcing Hebrew labels onto Greek.

### Query-oriented clause index: `clauses[]`

This is derived from `nodes[]` and must be regenerated/validated against it. It exposes `clause_id`, `sentence_id`, `parent_clause_id`, coverage, sequence, token span, depth, category/type/function, and text. Ordered `token_ids` preserves discontinuity. Do not use this flattened index to recreate the tree.

### Reference and semantic data

`reference_links[]` records only comparison relations to MACULA Greek or another approved treebank, including dataset, revision, target ID, relation, and evidence. It cannot store a primary token ID.

Future semantic tables (roles, referents, senses, discourse) reference `token_id` or `node_id`; they are not embedded as syntax rules or needed for a syntax document to validate.

## Deterministic derived representations

| Representation | Derivation | Independently editable? |
| --- | --- | --- |
| Nested nodes | Canonical document | Yes, through controlled syntax editing |
| Lowfat XML/JSON | Preorder traversal of canonical nodes | No; regenerate |
| TSV | Ordered terminal traversal plus morphology | No; regenerate |
| Clause table | Clause-node traversal | No; regenerate |

The lowfat projection needs explicit `id` and `parent_id` even though MACULA lowfat often relies on XML nesting. This prevents identity loss when a query system flattens XML.

## Validation rules

1. Every token reference resolves exactly once; source ordinals are unique in their source verse.
2. Each syntax node exists once; every non-root node has exactly one parent; no cycles.
3. A terminal has exactly one `token_id`; every token is covered once by a terminal word node.
4. A node's terminal yield is in canonical token order unless expressly `discontinuous`; ordered `token_ids` still make its span checkable.
5. Every clause index row resolves to a `kind="clause"` node and agrees on yield, parent clause, and depth.
6. Surface plus `after` reconstruct punctuation/whitespace; punctuation does not decide clause boundaries.
7. Every non-trivial clause decision has evidence. A reference link alone is not sufficient evidence.

The JSON Schema validates shape. A corpus validator must additionally check graph relationships, yield coverage, and source reconstruction.

## Vocabulary policy

The prototype may use observed MACULA-style labels `cl`, `np`, `pp`, `vp`, `adjp`, `advp`, `s`, `v`, `o`, `io`, and `adv` where they accurately describe TR Greek. New labels need a versioned vocabulary entry with definition, language applicability, examples, and approver. Do not invent labels merely to mirror an upstream tree.

