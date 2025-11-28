# buycrypto

A minimal Coinbase Advanced Trade bot that watches the BTC-USD price and places a one-time limit buy when your target is reached.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Provide API credentials (View + Trade permissions only):
   ```bash
   export COINBASE_API_KEY="organizations/{org_id}/apiKeys/{key_id}"
   export COINBASE_API_SECRET="-----BEGIN EC PRIVATE KEY-----\n...\n-----END EC PRIVATE KEY-----\n"
   ```

   You can alternatively create a `.env` file with the same variable names for local development.

## Usage

Update the configuration values at the top of `btc_bot.py` if you want a different target price, spend amount, or poll interval, then run:

```bash
python btc_bot.py
```

The script will poll `BTC-USD` every `POLL_INTERVAL` seconds. When the current price is at or below `TARGET_PRICE`, it submits a Good-Til-Canceled limit buy sized to spend approximately `USD_TO_SPEND`, logs the raw response, and exits.
