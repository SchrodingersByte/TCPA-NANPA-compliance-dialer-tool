"""
Mock National DNC list generator.

Produces 100,000 unique, seeded-random E.164 phone numbers and writes them to
data/mock_dnc_list.csv.  The Random seed is fixed so the output is reproducible
across runs — the same call to generate() always produces the same file.

Usage:
    python data/generate_dnc.py

The output file is consumed by app/services/compliance_engine.load_dnc_cache()
at application startup.
"""

import csv
import random
import sys
from pathlib import Path

# Make the project root importable when running this script directly.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from app.core.timezone_maps import AREA_CODE_MAP  # noqa: E402

OUTPUT_PATH = _PROJECT_ROOT / "data" / "mock_dnc_list.csv"
TARGET_COUNT = 100_000
RANDOM_SEED = 42  # fixed for reproducibility


def generate(output_path: Path = OUTPUT_PATH, target: int = TARGET_COUNT) -> int:
    """
    Generate `target` unique E.164 NANPA numbers and write to `output_path`.
    Returns the number of rows written (excluding the header).
    """
    area_codes = list(AREA_CODE_MAP.keys())
    rng = random.Random(RANDOM_SEED)
    numbers: set[str] = set()

    while len(numbers) < target:
        area_code = rng.choice(area_codes)
        # Exchange code: 200–999 (NANPA mandates area/exchange codes never start with 0 or 1)
        exchange = rng.randint(200, 999)
        # Subscriber number: 0000–9999
        subscriber = rng.randint(0, 9999)
        number = f"+1{area_code}{exchange:03d}{subscriber:04d}"
        numbers.add(number)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["phone_number"])
        for num in sorted(numbers):
            writer.writerow([num])

    return len(numbers)


if __name__ == "__main__":
    print(f"Generating {TARGET_COUNT:,} mock DNC entries...")
    count = generate()
    print(f"Done. {count:,} numbers written to {OUTPUT_PATH}")
