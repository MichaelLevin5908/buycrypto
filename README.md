# buycrypto

A minimal Coinbase Advanced Trade bot that watches the BTC-USD price and places a one-time limit buy when your target is reached.

## Setup

1. Install dependencies:
   ```bash
   pip install -r constraints.txt
   ```

2. Provide API credentials (View + Trade permissions only):
   * If you downloaded the Coinbase JSON file, point the environment variable to it:
     ```bash
     export COINBASE_API_JSON_PATH="/path/to/cdp_api_key.json"  # contains id + privateKey
     ```

   You can alternatively create a `.env` file with the same variable names for local development.

## Usage

Update the configuration values at the top of `btc_bot.py` if you want a different target price, spend amount, or poll interval, then run:

```bash
python btc_bot.py
```

The script will poll `BTC-USD` every `POLL_INTERVAL` seconds. When the current price is at or below `TARGET_PRICE`, it submits a Good-Til-Canceled limit buy sized to spend approximately `USD_TO_SPEND`, logs the raw response, and exits.

## What funds are used?

Trades are submitted through Coinbase Advanced Trade using the API key you provide. Orders can only draw from the balances and permissions of that Coinbase account (for example, your USD balance or USDC). The bot itself has no ability to initiate transfers from a linked bank account.
