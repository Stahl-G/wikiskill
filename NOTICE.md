# Attribution

This is an independent implementation of **WikiSkill: Compiling Agent Experience into Persistent Knowledge for Skill Evolution**, Liyan Tang et al., arXiv:2608.27454 (2026). Cite the paper when building on the method. The paper's prompt format and algorithm are adapted here; this repository is not affiliated with the paper's authors.

The benchmark adapters, Wiki edit/proposal contracts and portions of the experiment harness were extracted and adapted from **Stahl-G/briefloop**, © 2026 multi-agent-brief-workflow contributors, MIT. The original notice is retained in LICENSE. `docs/source-provenance.json` identifies source files and their byte hashes before extraction; namespace, packaged paths and the portable driver have changed.

`src/wikiskill/officeqa/reward.py` is a vendored Databricks OfficeQA scorer. Its Apache-2.0 license and upstream notice are in `third_party/officeqa/`. The vendored scorer's bytes are retained from the source experiment; it is not silently updated to the latest upstream code.

OfficeQA source: https://github.com/databricks/officeqa

Split identifiers and benchmark attribution are in the packaged resource manifests. Large datasets, restricted answer keys, raw source documents, private business materials and model credentials are not distributed here. Synthetic test fixtures are software checks, not research results.
