import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import extract  # noqa: E402
from load import load_raw  # noqa: E402

FAKE = [
    {
        "id": "bitcoin",
        "symbol": "btc",
        "current_price": 60000.0,
        "market_cap": 1.0e12,
        "total_volume": 3.0e10,
        "price_change_percentage_24h": 1.5,
        "last_updated": "2026-11-04T08:00:00Z",
        "champ_inutile": "ignoré",
    }
]


class FakeResp:
    def raise_for_status(self):
        pass

    def json(self):
        return FAKE


def test_fetch_keeps_only_known_fields(monkeypatch):
    monkeypatch.setattr(extract.requests, "get", lambda *a, **k: FakeResp())
    rows = extract.fetch_markets(["bitcoin"], "eur")
    assert rows[0]["id"] == "bitcoin"
    assert "champ_inutile" not in rows[0]


def test_load_appends_rows(tmp_path):
    db = tmp_path / "t.duckdb"
    rows = [{k: v for k, v in FAKE[0].items() if k in extract.FIELDS}]
    load_raw(rows, db)
    load_raw(rows, db)  # 2e exécution : on ajoute, on n'écrase pas
    con = duckdb.connect(str(db))
    assert con.execute("SELECT count(*) FROM raw.prices").fetchone()[0] == 2
    assert con.execute("SELECT loaded_at FROM raw.prices").fetchone()[0] is not None
