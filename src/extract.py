import requests

URL = "https://api.coingecko.com/api/v3/coins/markets"
FIELDS = [
    "id",
    "symbol",
    "current_price",
    "market_cap",
    "total_volume",
    "price_change_percentage_24h",
    "last_updated",
]


def fetch_markets(coins, vs_currency, api_key=None):
    """Retourne une liste de dicts (un par crypto) avec les champs de FIELDS."""
    headers = {"x-cg-demo-api-key": api_key} if api_key else {}
    params = {"vs_currency": vs_currency, "ids": ",".join(coins)}
    resp = requests.get(URL, params=params, headers=headers, timeout=30)
    resp.raise_for_status()  # 429 = rate limit, on laisse l'erreur remonter
    return [{f: item.get(f) for f in FIELDS} for item in resp.json()]
