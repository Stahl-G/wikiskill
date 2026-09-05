# Contributor instructions

WikiSkill is an independent, multi-domain research framework. Keep the package standalone: no dependency on another local checkout or personal configuration files.

- Model agents produce Wiki edits and proposals; deterministic code owns scoring, gating and experiment records.
- Keep failed attempts and rejected proposals inspectable. Do not rewrite frozen research snapshots.
- Treat train/validation selection and held-out evaluation as different evidence. Do not turn missing results into zeros or describe validation gains as established statistical significance.
- Keep data, runtime credentials and local runs out of Git. Use synthetic fixtures for software checks.
- Run focused offline tests for behavior changes. For packaging changes, verify one installed-package demo and result recomputation from outside the source tree. Do not launch paid model experiments merely to reassure a code change.
- Update both README.md and README_zh-CN.md when user-facing behavior changes.
- Imported historical results came from the originating harness; label any subsequent runner or scoring changes instead of implying those results were remeasured.
