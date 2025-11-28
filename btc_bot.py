import os
import time
import uuid
from typing import Optional

from coinbase.rest import RESTClient
from dotenv import load_dotenv

# === CONFIGURE THESE ===
TARGET_PRICE = 85_000.0  # Buy when BTC-USD <= this price
USD_TO_SPEND = 50.0      # How many USD to spend once
POLL_INTERVAL = 10       # Seconds between price checks
PRODUCT_ID = "BTC-USD"   # Trading pair
# ========================


def get_client() -> RESTClient:
    """Create a REST client using API credentials from environment variables.

    Exits early with a clear error if the variables are missing to avoid
    placing unintended orders.
    """

    # Allow users to keep secrets in a .env file for local development.
    load_dotenv()

    api_key = os.environ.get("COINBASE_API_KEY")
    api_secret = os.environ.get("COINBASE_API_SECRET")

    if not api_key or not api_secret:
        raise RuntimeError(
            "Missing COINBASE_API_KEY or COINBASE_API_SECRET environment variables."
        )

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
    print(f"Will spend  : {USD_TO_SPEND:.2f} USD one time\n")

    while True:
        try:
            price = get_current_price(client, PRODUCT_ID)
            print(f"Current price: {price:.2f} USD")

            if price <= TARGET_PRICE:
                print("\n🎯 Target hit! Placing buy order...")
                place_limit_buy(client, PRODUCT_ID, TARGET_PRICE)
                break  # stop after one buy
        except Exception as exc:  # noqa: BLE001 - surface any issues clearly to the user
            print(f"\n[ERROR] {exc}\n")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
