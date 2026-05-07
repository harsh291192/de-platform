import time
from typing import Generator

import pandas as pd
import requests


def fetch_paginated_api(base_url: str, api_key: str) -> Generator[dict, None, None]:
    """Fetch all pages from a paginated API — yields records lazily."""
    page = 1
    while True:
        response = requests.get(
            base_url,
            params={"page": page, "per_page": 1000},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        records = data.get("results", [])
        if not records:
            break
        yield from records
        page += 1
        time.sleep(0.1)


# Usage
records = list(fetch_paginated_api("https://api.example.com/orders", "my_key"))
df = pd.DataFrame(records)
df.to_parquet("raw/orders.parquet")
