import os

from dotenv import load_dotenv

from extract import fetch_markets
from load import load_raw

load_dotenv()

if __name__ == "__main__":
    coins = os.environ["COINS"].split(",")
    rows = fetch_markets(
        coins, os.environ["VS_CURRENCY"], os.getenv("COINGECKO_API_KEY") or None
    )
    n = load_raw(rows, os.environ["DUCKDB_PATH"])
    print(f"{n} lignes chargées dans raw.prices")
