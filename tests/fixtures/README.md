# Test fixtures

Tiny synthetic images for unit/contract tests are generated at test time via
Pillow (see `tests/contracts/`). Golden expected strings for parsing helpers
live alongside the unit tests in `tests/unit/`.

GPU smoke fixtures are not committed; use host sample pages under
`/root/workspace/samples` or OmniDocBench subsets.
