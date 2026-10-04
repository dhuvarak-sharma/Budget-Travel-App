"""
api_utils.py
------------
This file talks to a REAL, free, no-signup-required web API to get the
current USD -> INR exchange rate. This is needed because our database
stores international destination prices in USD, but the user enters
their budget in INR.

API used: https://open.er-api.com/v6/latest/USD
(No API key needed, no payment needed, works for a school project.)

If the internet is not available, or the API is down, the program does
NOT crash -- it falls back to a fixed offline exchange rate so the rest
of the program still works. This satisfies the "works offline if
possible" requirement: destination search itself always works offline
(pure MySQL), only this one live-price feature needs the internet, and
it degrades gracefully when there is none.

Only Python's built-in libraries are used (urllib, json) -- no extra
packages need to be installed for this file.
"""

import urllib.request
import json

# Used only if the internet / API is unavailable.
FALLBACK_USD_TO_INR = 83.0

EXCHANGE_API_URL = "https://open.er-api.com/v6/latest/USD"


def get_usd_to_inr_rate():
    """
    Tries to fetch the live USD -> INR rate from a free public API.
    Returns (rate, is_live) where is_live tells the caller whether the
    rate came from the internet (True) or the offline fallback (False).
    """
    try:
        # timeout=5 -> don't let the whole program freeze if internet is slow
        with urllib.request.urlopen(EXCHANGE_API_URL, timeout=5) as response:
            data = json.loads(response.read().decode())
            rate = data["rates"]["INR"]
            return float(rate), True
    except Exception as error:
        # Covers: no internet, API down, unexpected response format, etc.
        print(f"[INFO] Could not fetch live exchange rate ({error}). "
              f"Using offline fallback rate of {FALLBACK_USD_TO_INR}.")
        return FALLBACK_USD_TO_INR, False


def convert_to_inr(amount, currency, usd_to_inr_rate):
    """
    Converts 'amount' from its own currency into INR.
    Right now the database only ever uses 'INR' or 'USD', so this
    function only needs to handle those two cases.
    """
    if currency == "INR":
        return amount
    elif currency == "USD":
        return amount * usd_to_inr_rate
    else:
        # Safety net for any currency we don't explicitly support yet.
        raise ValueError(f"Unsupported currency: {currency}")


# ---------------------------------------------------------------------
# MULTI-CURRENCY CONVERTER
# (used only by the standalone Currency Converter window in main.py --
#  the destination search above keeps using get_usd_to_inr_rate() /
#  convert_to_inr() exactly as before, untouched)
# ---------------------------------------------------------------------

# Used only if the internet / the live-rates API is unavailable.
# Each value means "1 USD buys this many units of that currency".
# These are approximate, fixed values -- good enough for a school project.
FALLBACK_RATES_PER_USD = {
    "USD": 1.0,
    "INR": 83.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "JPY": 149.0,
}

# The currencies the Currency Converter window lets the user pick from.
SUPPORTED_CURRENCIES = list(FALLBACK_RATES_PER_USD.keys())


def get_live_rates():
    """
    Tries to fetch live exchange rates (base currency = USD) from the same
    free public API used above for the USD -> INR rate. Only the 5
    currencies this app supports are kept from the response.

    Returns (rates, is_live) where rates is a dict like
    {"USD": 1.0, "INR": 83.2, "EUR": 0.91, ...} and is_live tells the
    caller whether these came from the internet (True) or the offline
    fallback (False). If anything goes wrong, falls back to
    FALLBACK_RATES_PER_USD so the converter keeps working offline.
    """
    try:
        with urllib.request.urlopen(EXCHANGE_API_URL, timeout=5) as response:
            data = json.loads(response.read().decode())
            live_rates = data["rates"]
            rates = {code: float(live_rates[code]) for code in SUPPORTED_CURRENCIES}
            return rates, True
    except Exception as error:
        # Covers: no internet, API down, a currency missing from the
        # response, unexpected response format, etc.
        print(f"[INFO] Could not fetch live exchange rates ({error}). "
              f"Using offline fallback rates.")
        return dict(FALLBACK_RATES_PER_USD), False


def convert_currency(amount, from_currency, to_currency, rates_per_usd):
    """
    Converts 'amount' from from_currency to to_currency using a
    rates_per_usd dictionary (as returned by get_live_rates()), where
    every value means "1 USD = this many units of that currency".

    Works for any pair of supported currencies (not just USD/INR) by
    converting through USD as a common base currency.
    """
    if from_currency not in rates_per_usd or to_currency not in rates_per_usd:
        raise ValueError("Unsupported currency.")

    amount_in_usd = amount / rates_per_usd[from_currency]
    return amount_in_usd * rates_per_usd[to_currency]
