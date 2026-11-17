# Provenance: first-century Greek literary controls

This directory records two **literary**, not documentary, controls used for
named-human lexical research. They are not textual authorities for the New
Testament and are not inputs to the automatic translation packet.

## Pinned sources

| Source | Repository and commit | Pinned tree | Greek editions | License |
| --- | --- | --- | ---: | --- |
| Philo of Alexandria | Open Greek and Latin `First1KGreek`, `ed91552c52530c8f5a3ddf2dd767e899372a804c` | `data/tlg0018` = `b2a2da4948b64595e61535587232eadb3f6761e7` | 31 | CC BY-SA 4.0 |
| Flavius Josephus | PerseusDL `canonical-greekLit`, `7fd4dae30f1d2176c3c6f64c0750f6f39cd972f3` | `data/tlg0526` = `0c7e87bac2f60bf603d4d97802776ce2b354b1a1` | 4 | CC BY-SA 4.0 |
| Plutarch | same PerseusDL commit | `data/tlg0007` = `fa7006cae3945e83e4361ba9bec5335e96fa6efd` | 143 | CC BY-SA 4.0 |
| Dio Chrysostom | same PerseusDL commit | `data/tlg0612` = `decea3a69159037e29c9e416c6f6c953042103b5` | 1 | CC BY-SA 4.0 |
| Epictetus, transmitted by Arrian | same PerseusDL commit | `data/tlg0557` = `aeb755f13c116e5e426736a2a66f217ecf4a09b7` | 5 | CC BY-SA 4.0 |

The exact allowlist, file counts and aggregate Git-blob hashes are in
[`LITERARY_KOINE_MANIFEST.json`](LITERARY_KOINE_MANIFEST.json). Only paths
whose edition filename contains `grc` are selected. Parallel `eng` files are
excluded mechanically. The tool also excludes TEI notes, apparatus readings,
deletions and front matter from the searched text.

Eleven Plutarch work directories contain two parallel Greek editions. To
avoid counting the same work twice, the inventory selects the first numbered
Greek CTS edition in each work directory and pins the resulting 143-file set
by aggregate hash. This is a reproducible anti-duplication rule, not a claim
that the selected edition is textually superior.

The digital Philo editions identify the print editors work by work, chiefly
the Cohn/Wendland *Philonis Alexandri Opera Quae Supersunt*. The Josephus
editions identify Benedikt Niese's *Flavii Iosephi Opera*. The inventory
retains the digital edition URN and exact XML path so every occurrence can be
checked against that edition.

## Method and limits

[`literary_koine_inventory.py`](../../../tools/research/literary_koine_inventory.py)
verifies the checkout commit, author tree, clean state, exact Greek file set
and aggregate hash before searching. It normalizes case and diacritics only
for discovery. Every result preserves the printed surface, CTS passage,
immediate Greek context and source path. It assigns no lemma, morphology,
gloss, semantic role or Spanish equivalent.

These witnesses represent different literary registers:

- Philo: first-century Alexandrian Jewish philosophical and exegetical prose;
- Josephus: first-century Jewish historical and apologetic prose.
- Plutarch: late-first/early-second-century Greco-Roman biography and moral
  philosophy;
- Dio Chrysostom: late-first/early-second-century Greco-Roman oratory;
- Epictetus as transmitted by Arrian: early-second-century dialogical
  philosophy.

They must not be described as everyday documentary Greek. Their frequencies
remain separate from DDbDP and from one another. Immediate linguistic context
is required to understand an occurrence; theological interpretation is not
part of this concordance.

`modelExposed: false` in an inventory means that the evidence was not inserted
into a Team Desk or canonical translation-model packet. The research
assistant did inspect the primary Greek contexts while building and auditing
the inventory; this is recorded separately in [`CONSULTATIONS.json`](CONSULTATIONS.json).

