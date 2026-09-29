"""Seed/check a document row around the mainline-to-integrated migration upgrade."""

from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine, text

USER_ID = 910001
DOCUMENT_ID = 910001


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"seed", "check"}:
        raise SystemExit("usage: python scripts/check_migration_document_preservation.py seed|check")
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    engine = create_engine(database_url)
    with engine.begin() as connection:
        if sys.argv[1] == "seed":
            connection.execute(
                text(
                    """
                    INSERT INTO users (
                        id, email, password_hash, role, is_verified, created_at,
                        verification_status, is_active
                    ) VALUES (
                        :id, 'migration-preservation@example.com', 'test-hash',
                        'worker', TRUE, CURRENT_TIMESTAMP, 'approved', TRUE
                    )
                    """
                ),
                {"id": USER_ID},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO visa_documents (
                        id, user_id, filename, file_path, file_type, status,
                        reviewer_id, review_note, created_at, waiver_acknowledged
                    ) VALUES (
                        :id, :user_id, 'migration-source.pdf', 'stored/123.pdf',
                        'application/pdf', 'pending', NULL, NULL, CURRENT_TIMESTAMP, TRUE
                    )
                    """
                ),
                {"id": DOCUMENT_ID, "user_id": USER_ID},
            )
        else:
            row = connection.execute(
                text(
                    """
                    SELECT user_id, filename, file_path, file_type, status,
                           waiver_acknowledged
                    FROM visa_documents WHERE id = :id
                    """
                ),
                {"id": DOCUMENT_ID},
            ).mappings().one_or_none()
            expected = {
                "user_id": USER_ID,
                "filename": "migration-source.pdf",
                "file_path": "stored/123.pdf",
                "file_type": "application/pdf",
                "status": "pending",
                "waiver_acknowledged": True,
            }
            if row is None or dict(row) != expected:
                raise SystemExit(f"verification document was not preserved: {row!r}")
            print("Existing verification document survived migration upgrade.")
    engine.dispose()


if __name__ == "__main__":
    main()
