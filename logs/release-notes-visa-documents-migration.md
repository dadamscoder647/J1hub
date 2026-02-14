# Release Notes: Visa Documents Corrective Migration

## Summary

A corrective update was applied to migration `d4d19a25492d` so the `visa_documents` table is migrated in place instead of being dropped and recreated.

## What changed

- Legacy columns are transformed to the new schema using rename/add/backfill steps:
  - `file_url` -> `file_path`
  - `notes` -> `review_note`
  - `doc_type` values are backfilled into new `file_type`
  - `filename` is backfilled from `file_path` (`basename` on PostgreSQL, full path fallback on SQLite)
  - legacy status `denied` is mapped to `rejected`
- The migration keeps existing rows and then applies the new non-null constraints/index.

## Data migration expectations

- Existing `visa_documents` rows are preserved.
- `doc_type='passport'` migrates to `file_type='passport'`.
- `doc_type='j1_visa'` migrates to `file_type='j1_visa'`.
- Any unexpected `doc_type` value migrates to `file_type='other'`.
- Existing `notes` content is preserved in `review_note`.
- Existing `file_url` content is preserved in `file_path`.

## Required operational safeguard

**Take a full database backup (or snapshot) before applying this migration in staging/production.**

Even though this migration is in-place and non-destructive by design, backups are required for rollback safety and validation.
