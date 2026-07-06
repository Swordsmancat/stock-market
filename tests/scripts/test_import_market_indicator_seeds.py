import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.domain.models import MarketIndicatorObservation
from packages.services.market_indicators import get_latest_market_indicator_payload
from packages.shared.database import Base
from scripts import import_market_indicator_seeds


def make_session_factory():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_import_market_indicator_seeds_script_imports_seed_file(tmp_path, capsys):
    session_factory = make_session_factory()
    seed_file = tmp_path / "macro-seeds.json"
    seed_file.write_text(
        json.dumps(
            [
                {
                    "code": "cn_m2_yoy",
                    "as_of": "2026-06-30",
                    "value": "8.300000",
                    "source": "Audited seed: PBOC public monetary statistics",
                    "components": {
                        "source_url": "https://example.com/pboc-m2-release",
                        "methodology": "Manual YoY value reviewed from public release.",
                    },
                }
            ]
        ),
        encoding="utf-8",
    )

    exit_code = import_market_indicator_seeds.main(
        [str(seed_file)],
        session_factory=session_factory,
    )

    output = capsys.readouterr().out
    with session_factory() as session:
        payload = get_latest_market_indicator_payload("cn_m2_yoy", session=session)

    assert exit_code == 0
    assert "OK imported 1 macro indicator observations" in output
    assert str(seed_file) in output
    assert payload["status"] == "ok"
    assert payload["value"] == 8.3


def test_import_market_indicator_seeds_script_reports_validation_failure(tmp_path, capsys):
    session_factory = make_session_factory()
    seed_file = tmp_path / "macro-seeds.json"
    seed_file.write_text(
        json.dumps(
            [
                {
                    "code": "cn_m2_yoy",
                    "as_of": "2026-06-30",
                    "value": "8.300000",
                    "source": "Audited seed: PBOC public monetary statistics",
                    "components": {"source_url": "https://example.com/pboc-m2-release"},
                }
            ]
        ),
        encoding="utf-8",
    )

    exit_code = import_market_indicator_seeds.main(
        [str(seed_file)],
        session_factory=session_factory,
    )

    output = capsys.readouterr().out
    with session_factory() as session:
        observation_count = session.query(MarketIndicatorObservation).count()

    assert exit_code == 1
    assert "FAIL seed import" in output
    assert "components must include one of" in output
    assert observation_count == 0
