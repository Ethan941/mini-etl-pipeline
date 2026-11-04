from pathlib import Path

import duckdb

from extract import FIELDS


def load_raw(rows, db_path):
    """Ajoute les lignes brutes dans raw.prices, avec la date de chargement."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute(
        """CREATE TABLE IF NOT EXISTS raw.prices (
            id VARCHAR, symbol VARCHAR, current_price DOUBLE, market_cap DOUBLE,
            total_volume DOUBLE, price_change_percentage_24h DOUBLE,
            last_updated VARCHAR, loaded_at TIMESTAMP DEFAULT now())"""
    )
    cols = ", ".join(FIELDS)
    marks = ", ".join("?" for _ in FIELDS)
    con.executemany(
        f"INSERT INTO raw.prices ({cols}) VALUES ({marks})",
        [[r[f] for f in FIELDS] for r in rows],
    )
    con.close()
    return len(rows)
