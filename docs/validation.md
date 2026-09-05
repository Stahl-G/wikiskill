# Release validation

Checked locally on 2026-09-05 with Python 3.14, pydantic 2.13.5 and pytest 9.1.1.

- Focused inherited adapter and new driver checks: **47 passed, 4 skipped**. The skipped cases require separately installed external benchmark datasets/environments and are opt-in through `WIKISKILL_TEST_DATA`.
- A non-editable wheel was built and installed into a separate virtual environment.
- Outside the checkout, with isolated Python import paths, the installed package completed its synthetic ACCEPT / REJECT / no_action demo.
- Installed-package result verification successfully recomputed all **18 baseline-bearing cells** and selected-skill hashes in the bundled snapshot.
- Both README files were checked for local links. Release content was scanned for the source machine's account paths and credential markers.

No paid model calls, new benchmark claims, or held-out evaluations were made for packaging validation. The preserved historical experiments were not rerun. CI is configured for Python 3.11 and 3.12; local results do not claim those hosted jobs have already passed.
