# Reproduction and portability

## Two distinct records

The bundled research snapshot was measured in the original Codex-based experiment harness. The import script exports only train/val scores, task identifiers, model-echo metadata, gate metadata and selected skills. Source hashes support provenance; the export does not reproduce full model trajectories or prove the absence of every possible leakage route.

This package supplies the extracted adapters plus a new shared entry point. The portable entry was verified with offline tests, deterministic demo and a non-editable wheel installation. The historical model matrix has not been rerun with the new driver.

The new driver uses immutable manifest configuration, unique attempt directories, an authoritative append-only event log and recoverable Wiki impact projection. It resumes completed cases and preserves infrastructure failures. It does not automatically repeat failed calls forever; after the underlying problem is resolved, re-run `evolve` to resume. If the process is interrupted during Maintainer file application before its completion marker, inspect the retained `wiki-before` snapshot and Maintainer outputs before resuming. A partially applied edit is not a successful iteration.

## What changed from the source experiments

- The Python namespace is now `wikiskill`; datasets are caller-supplied and prompts/split metadata are packaged resources.
- Audit-only BriefLoop dependencies are removed; the shared agent structural contracts are extracted independently.
- A common CLI drives the bundled domains. Legacy domain loop modules remain available for method comparison and provenance.
- The portable driver preserves inference attempts separately instead of reusing the same scratch directory.
- New empty-skill hashes use SHA-256 of empty bytes. Historical artifacts retain their original conventions, including zero-string sentinels where originally recorded.
- Agent-facing gate history is reconstructed from committed events if its projection is missing.

These changes are disclosed, not treated as new measured model gains.

## Interpretation of the experiment matrix

The paper reports test performance averaged over three independent complete evolutions. The bundled local matrix has one evolution per domain/model and adaptively reused small validation sets. Its validation delta is descriptive. Repeated inference with one frozen skill is not repeated independent evolution.

The fixed optimizer in the source experiments is Sol/medium; the portable CLI records its optimizer explicitly, defaulting to the requested inference model unless `--optimizer-model` is supplied. Use Sol/medium to match the documented source configuration. The default cap is 200 skill lines and 150 changed diff lines; prior source attempts used 80/60 and their deviations remain disclosed.

## Extending a domain

Implement a split loader that returns unique task IDs and a rollout callable. It must return `uid`, binary `score`, `fail_reason`, `model`, `reported_model`, `skill_sha256`, and `workspace`. Infrastructure failures must not masquerade as wrong answers. Stage only task inputs to the inference agent; gold answers belong to the scorer. Use domain-specific Maintainer/Proposer prompts and test the scorer with known correct, wrong and malformed outputs before model batches.

`engine.batch` and the Wiki agent factories are reusable Python entry points. `engine.load_domain` is the current bundled registry; external domain auto-discovery is not implemented. `engine.evolve` reads train and val only. Independent held-out campaigns should use a separately frozen design and driver; this release does not pretend its training CLI is a completed confirmatory test runner.

## Execution boundary

The Codex backend uses `codex exec` with the runtime's workspace-write sandbox and stages data in an experiment workspace. Prompt restrictions and staging are not a complete filesystem or network isolation proof. Use a separately configured runtime/container when stronger access isolation is required. Do not mount answer keys, experiment evaluator state or hidden test data into model-readable workspaces.

Model identities are opaque runtime names; the project checks available echoes but cannot guarantee account-level availability. `doctor` only locates the executable. No credential is stored in the repository.
