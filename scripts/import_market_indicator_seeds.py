"""Import reviewed macro/valuation indicator seed files into the database."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TextIO

from sqlalchemy.orm import Session

from packages.services.market_indicators import (
    MarketIndicatorSeedImportError,
    import_market_indicator_observation_seed_file,
)
from packages.shared.database import SessionLocal


SessionFactory = Callable[[], Session]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Import a reviewed JSON or CSV macro indicator seed file. "
            "This writes audited observations to the configured database."
        ),
    )
    parser.add_argument(
        "seed_file",
        type=Path,
        help="Path to a reviewed .json or .csv seed file.",
    )
    return parser


def import_seed_file(seed_file: Path, session_factory: SessionFactory) -> int:
    session = session_factory()
    try:
        result = import_market_indicator_observation_seed_file(seed_file, session=session)
    finally:
        session.close()
    return result.observations


def main(
    argv: Sequence[str] | None = None,
    *,
    output: TextIO | None = None,
    session_factory: SessionFactory = SessionLocal,
) -> int:
    output_stream = output if output is not None else sys.stdout
    args = build_parser().parse_args(argv)

    try:
        imported_count = import_seed_file(args.seed_file, session_factory)
    except MarketIndicatorSeedImportError as error:
        print(f"FAIL seed import: {error}", file=output_stream)
        return 1
    except OSError as error:
        print(f"FAIL seed import: {error}", file=output_stream)
        return 1

    print(
        f"OK imported {imported_count} macro indicator observations from {args.seed_file}",
        file=output_stream,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
