#!/usr/bin/env python3
"""One-off generator for synthetic user profiles (demographics + address; no balances).

Writes a JSON array for local use or for manual upload to S3 under ``users/``.

Example:
  python scripts/generate_user_profiles.py --count 9999 --seed 42 \\
    --output app/data/user_profiles.json

In AWS, profiles are normally loaded from S3 (see README); the app will create the
object if missing when the bucket env vars are set.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.user_profiles_dataset import build_profiles


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=99999, help="Number of profiles (user_id 1..N)")
    parser.add_argument("--seed", type=int, default=42, help="Base seed for reproducibility")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("app/data/user_profiles.json"),
        help="Output JSON path (array of profile objects)",
    )
    args = parser.parse_args()

    if args.count < 1:
        raise SystemExit("--count must be >= 1")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    profiles = build_profiles(args.count, args.seed)
    args.output.write_text(json.dumps(profiles, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(profiles)} profiles to {args.output}")


if __name__ == "__main__":
    main()
