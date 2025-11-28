import json
import os
import time
import uuid
from pathlib import Path
from typing import Optional

from coinbase.rest import RESTClient
from dotenv import load_dotenv

# === CONFIGURE THESE ===
TARGET_PRICE = 90_000.0  # Buy when BTC-USD <= this price
USD_TO_SPEND = 100.0      # How many USD to spend once
POLL_INTERVAL = 10       # Seconds between price checks
PRODUCT_ID = "BTC-USD"   # Trading pair
BUY_COOLDOWN = 604800     # Seconds to wait after a buy before checking again (1 week)
# ========================


def load_credentials_from_json(path: str) -> tuple[str, str]:
    """Load an API key and secret from a Coinbase JSON file."""

    json_path = Path(path).expanduser()
    if not json_path.exists():
        raise RuntimeError(f"COINBASE_API_JSON_PATH does not exist: {json_path}")

    try:
        raw = json_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except Exception as exc:  # pragma: no cover - defensive parsing
        raise RuntimeError(
            f"Failed to read or parse JSON credentials at {json_path}: {exc}"
        ) from exc

    try:
        api_key = data["id"]
        api_secret = data["privateKey"]
    except KeyError as exc:
        raise RuntimeError(
            "JSON credentials must contain 'id' and 'privateKey' fields from Coinbase."
        ) from exc

    api_key = str(api_key).strip()
    api_secret = str(api_secret).replace("\\n", "\n").strip()

    if not api_key or not api_secret:
        raise RuntimeError("Empty 'id' or 'privateKey' in JSON credentials.")

    return api_key, api_secret


def get_client() -> RESTClient:
    """Create a REST client using API credentials.

    Supports either:
    * `COINBASE_API_JSON_PATH` pointing to the downloaded JSON file that
      contains `id` and `privateKey`, or
    * `COINBASE_API_KEY` and `COINBASE_API_SECRET` environment variables.
    """

    # Allow users to keep secrets in a .env file for local development.
    load_dotenv()

    json_path = os.environ.get("COINBASE_API_JSON_PATH")
    if json_path:
        api_key, api_secret = load_credentials_from_json(json_path)
    else:
        api_key = os.environ.get("COINBASE_API_KEY")
        api_secret = os.environ.get("COINBASE_API_SECRET")

        if not api_key or not api_secret:
            raise RuntimeError(
                "Provide COINBASE_API_JSON_PATH or both COINBASE_API_KEY and COINBASE_API_SECRET."
            )

        api_key = api_key.strip()
        api_secret = api_secret.replace("\\n", "\n").strip()

    return RESTClient(api_key=api_key, api_secret=api_secret)


def get_current_price(client: RESTClient, product_id: str) -> float:
    """Fetch the current price for the given product using Advanced Trade data."""

    product = client.get_product(product_id)
    return float(product["price"])


def place_limit_buy(client: RESTClient, product_id: str, limit_price: float) -> Optional[str]:
    """Place a GTC limit buy order that spends roughly USD_TO_SPEND at limit_price."""

    base_size = USD_TO_SPEND / limit_price
    client_order_id = str(uuid.uuid4())

    print("\nPlacing limit BUY:")
    print(f"  Product      : {product_id}")
    print(f"  Limit price  : {limit_price:.2f} USD")
    print(f"  Base size    : {base_size:.8f} BTC")
    print(f"  Client order : {client_order_id}")

    order = client.limit_order_gtc_buy(
        client_order_id=client_order_id,
        product_id=product_id,
        base_size=f"{base_size:.8f}",  # BTC size
        limit_price=f"{limit_price:.2f}",  # USD price
    )

    print("\nRaw order response:")
    print(order)

    if order.get("success"):
        order_id = order["success_response"]["order_id"]
        print(f"\n✅ Order placed successfully! order_id = {order_id}")
        return order_id

    print("\n❌ Order failed.")
    print(order.get("error_response"))
    return None


def main() -> None:
    client = get_client()

    print(f"Watching {PRODUCT_ID}...")
    print(f"Target price: <= {TARGET_PRICE:.2f} USD")
    print(f"Will spend  : {USD_TO_SPEND:.2f} USD per buy")
    print(f"Buy cooldown: {BUY_COOLDOWN} seconds\n")

    last_buy_time = 0

    while True:
        try:
            price = get_current_price(client, PRODUCT_ID)
            print(f"Current price: {price:.2f} USD")

            time_since_last_buy = time.time() - last_buy_time
            if time_since_last_buy < BUY_COOLDOWN:
                remaining = BUY_COOLDOWN - time_since_last_buy
                print(f"On cooldown. Next buy check in {remaining:.0f} seconds.")
            elif price <= TARGET_PRICE:
                print("\n🎯 Target hit! Placing buy order...")
                order_id = place_limit_buy(client, PRODUCT_ID, TARGET_PRICE)
                if order_id:
                    last_buy_time = time.time()
                    print(f"Buy completed. Cooldown started.\n")
        except Exception as exc:
            print(f"\n[ERROR] {exc}\n")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
