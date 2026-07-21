"""BIDS validation internals.

The public entry point stays `bidsificator.services.ValidationServiceSchema`
(`ValidationService` + the `ValidationError`/`ValidationResult` dataclasses).
This package holds the pieces that facade delegates to:

- `report`         — the `ValidationError` / `ValidationResult` result types.
- `rules_files`    — file/structure rule checks (`FileRuleValidator`).
- `rules_metadata` — JSON-sidecar/metadata rule checks (`MetadataRuleValidator`).
- `_parsing`       — shared BIDS-filename parsing helpers.
"""
