import json
from pprint import pprint

import btc_bot

def main():
    client = btc_bot.get_client()

    # Try common balance/account methods on the client
    candidates = [
        "get_accounts",
        "list_accounts",
        "get_wallets",
        "get_balances",
        "get_all_accounts",
    ]

    for name in candidates:
        if hasattr(client, name):
            try:
                fn = getattr(client, name)
                res = fn() if callable(fn) else fn
                print(f"Using client.{name}() ->")
                try:
                    print(json.dumps(res, default=str, indent=2))
                except Exception:
                    pprint(res)
                return

            except Exception as e:
                print(f"client.{name}() raised: {e}")

    # Fallback: show available client attributes to help you pick a method
    attrs = [a for a in dir(client) if not a.startswith("_")]
    print("Could not call a known balance method. Client exposes these attributes/methods:")
    pprint(attrs)

if __name__ == "__main__":
    main()