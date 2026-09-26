"""Validate the repository's Render Blueprint against Render's published schema."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.request import urlopen

import jsonschema
import yaml

SCHEMA_URL = "https://render.com/schema/render.yaml.json"
ROOT_DIR = Path(__file__).resolve().parent.parent


def main() -> int:
    """Return a failing exit status if render.yaml does not match Render's schema."""
    with urlopen(SCHEMA_URL, timeout=30) as response:
        schema = json.load(response)

    blueprint = yaml.safe_load((ROOT_DIR / "render.yaml").read_text(encoding="utf-8"))
    validator_type = jsonschema.validators.validator_for(schema)
    validator_type.check_schema(schema)
    errors = sorted(
        validator_type(schema).iter_errors(blueprint),
        key=lambda error: [str(part) for part in error.path],
    )

    if errors:
        for error in errors:
            location = ".".join(str(part) for part in error.path) or "render.yaml"
            print(f"{location}: {error.message}")
        return 1

    print("render.yaml matches Render's published Blueprint schema.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
