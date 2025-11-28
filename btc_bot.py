import os
import json
import time
import uuid
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


def get_client() -> RESTClient:
    """Create REST client. Accepts:
      - COINBASE_API_SECRET (inline PEM)
      - COINBASE_API_SECRET_PATH (path to PEM file)
      - OR COINBASE_API_JSON_PATH (Coinbase JSON with id + privateKey)
    """
    load_dotenv()

    api_key = os.environ.get("COINBASE_API_KEY")
    api_secret = os.environ.get("COINBASE_API_SECRET")
    api_secret_path = os.environ.get("COINBASE_API_SECRET_PATH")
    api_json_path = os.environ.get("COINBASE_API_JSON_PATH")

    # If JSON file provided, load id and privateKey
    if api_json_path:
        try:
            with open(os.path.expanduser(api_json_path), "r") as f:
                jd = json.load(f)
        except Exception as e:
            raise RuntimeError(f"Cannot read JSON file {api_json_path}: {e}")

        api_key = jd.get("name")
        priv = jd.get("privateKey")
        if not priv:
            raise RuntimeError("No privateKey found in provided JSON.")

        # If JSON already contains PEM text, use it; otherwise format base64 into PEM block
        if "-----BEGIN" in priv:
            api_secret = priv
        else:
            b64 = priv.strip()
            lines = [b64[i:i+64] for i in range(0, len(b64), 64)]
            pem = "-----BEGIN PRIVATE KEY-----\n" + "\n".join(lines) + "\n-----END PRIVATE KEY-----\n"
            api_secret = pem

    # If path to PEM provided, read it
    if api_secret_path and not api_secret:
        try:
            with open(os.path.expanduser(api_secret_path), "r") as f:
                api_secret = f.read()
        except Exception as e:
            raise RuntimeError(f"Unable to read PEM at {api_secret_path}: {e}")

    if not api_key or not api_secret:
        raise RuntimeError("Missing COINBASE_API_KEY and/or COINBASE_API_SECRET (or provide COINBASE_API_SECRET_PATH or COINBASE_API_JSON_PATH).")

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
