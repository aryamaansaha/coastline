"""
Currency conversion utility for MCP server.

Converts all prices to USD for consistent budget calculations.
Uses Frankfurter API (free, no key required) with caching and fallback.
"""

import requests
import time
import logging
from typing import Optional

# Setup logging
logger = logging.getLogger(__name__)

# ============================================================================
# CACHE CONFIGURATION
# ============================================================================

_rate_cache: dict = {}
_cache_timestamp: float = 0
CACHE_DURATION_SECONDS = 3600  # 1 hour


# ============================================================================
# STATIC FALLBACK RATES (USD as base)
# These are approximate rates as of Dec 2024 - used only if API fails
# ============================================================================

STATIC_FALLBACK_RATES = {
    # Major currencies
    "USD": 1.0,
    "EUR": 1.08,      # Euro
    "GBP": 1.27,      # British Pound
    "JPY": 0.0067,    # Japanese Yen
    "CHF": 1.13,      # Swiss Franc
    "CAD": 0.74,      # Canadian Dollar
    "AUD": 0.65,      # Australian Dollar
    "NZD": 0.60,      # New Zealand Dollar
    
    # European currencies
    "DKK": 0.145,     # Danish Krone
    "SEK": 0.095,     # Swedish Krona
    "NOK": 0.091,     # Norwegian Krone
    "PLN": 0.25,      # Polish Zloty
    "CZK": 0.043,     # Czech Koruna
    "HUF": 0.0027,    # Hungarian Forint
    "RON": 0.22,      # Romanian Leu
    "BGN": 0.55,      # Bulgarian Lev
    "HRK": 0.14,      # Croatian Kuna (legacy, now EUR)
    "ISK": 0.0072,    # Icelandic Króna
    "TRY": 0.029,     # Turkish Lira
    "RUB": 0.011,     # Russian Ruble
    "UAH": 0.024,     # Ukrainian Hryvnia
    
    # Asian currencies
    "CNY": 0.14,      # Chinese Yuan
    "HKD": 0.128,     # Hong Kong Dollar
    "SGD": 0.74,      # Singapore Dollar
    "TWD": 0.031,     # Taiwan Dollar
    "KRW": 0.00075,   # South Korean Won
    "INR": 0.012,     # Indian Rupee
    "THB": 0.029,     # Thai Baht
    "MYR": 0.22,      # Malaysian Ringgit
    "IDR": 0.000063,  # Indonesian Rupiah
    "PHP": 0.018,     # Philippine Peso
    "VND": 0.00004,   # Vietnamese Dong
    
    # Middle East & Africa
    "AED": 0.27,      # UAE Dirham
    "SAR": 0.27,      # Saudi Riyal
    "ILS": 0.27,      # Israeli Shekel
    "EGP": 0.020,     # Egyptian Pound
    "ZAR": 0.055,     # South African Rand
    "MAD": 0.10,      # Moroccan Dirham
    "QAR": 0.27,      # Qatari Riyal
    "KWD": 3.26,      # Kuwaiti Dinar
    "BHD": 2.65,      # Bahraini Dinar
    "OMR": 2.60,      # Omani Rial
    
    # Americas
    "MXN": 0.058,     # Mexican Peso
    "BRL": 0.17,      # Brazilian Real
    "ARS": 0.0010,    # Argentine Peso
    "CLP": 0.0011,    # Chilean Peso
    "COP": 0.00024,   # Colombian Peso
    "PEN": 0.27,      # Peruvian Sol
}


# ============================================================================
# RATE FETCHING
# ============================================================================

def _fetch_live_rates() -> Optional[dict]:
    """
    Fetch live exchange rates from Frankfurter API.
    Returns dict mapping currency codes to USD conversion rates.
    Returns None if API call fails.
    """
    try:
        # Frankfurter API - free, no key needed
        # Get all rates with USD as base
        response = requests.get(
            "https://api.frankfurter.app/latest?from=USD",
            timeout=5  # 5 second timeout
        )
        response.raise_for_status()
        data = response.json()
        
        # API returns rates FROM USD, we need rates TO USD
        # So we invert: if 1 USD = 0.92 EUR, then 1 EUR = 1/0.92 USD
        rates = {"USD": 1.0}
        for currency, rate in data.get("rates", {}).items():
            if rate > 0:
                rates[currency] = round(1.0 / rate, 6)
        
        logger.info(f"✅ Fetched live exchange rates for {len(rates)} currencies")
        return rates
        
    except requests.exceptions.Timeout:
        logger.warning("⚠️ Currency API timeout - will use cache or fallback")
        return None
    except requests.exceptions.RequestException as e:
        logger.warning(f"⚠️ Currency API error: {e} - will use cache or fallback")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error fetching rates: {e}")
        return None


def get_exchange_rates() -> dict:
    """
    Get exchange rates with caching.
    Priority: Live API → Cached rates → Static fallback
    
    Returns:
        Dict mapping currency codes to USD conversion rates
    """
    global _rate_cache, _cache_timestamp
    
    current_time = time.time()
    cache_age = current_time - _cache_timestamp
    
    # Check if cache is valid
    if _rate_cache and cache_age < CACHE_DURATION_SECONDS:
        logger.debug(f"📦 Using cached rates (age: {int(cache_age)}s)")
        return _rate_cache
    
    # Try to fetch live rates
    live_rates = _fetch_live_rates()
    
    if live_rates:
        # Update cache with live rates
        _rate_cache = live_rates
        _cache_timestamp = current_time
        return live_rates
    
    # Live fetch failed - check if we have stale cache
    if _rate_cache:
        logger.warning(f"⚠️ Using stale cached rates (age: {int(cache_age)}s)")
        return _rate_cache
    
    # No cache available - use static fallback
    logger.warning("⚠️ Using static fallback rates (API unavailable, no cache)")
    return STATIC_FALLBACK_RATES.copy()


# ============================================================================
# CONVERSION FUNCTIONS
# ============================================================================

def convert_to_usd(amount: float, from_currency: str) -> float:
    """
    Convert an amount from any currency to USD.
    
    Args:
        amount: The amount to convert
        from_currency: The source currency code (e.g., "EUR", "GBP", "DKK")
    
    Returns:
        The amount converted to USD, rounded to 2 decimal places
    """
    if from_currency == "USD":
        return round(amount, 2)
    
    from_currency = from_currency.upper()
    rates = get_exchange_rates()
    
    if from_currency in rates:
        rate = rates[from_currency]
        converted = amount * rate
        logger.debug(f"💱 Converted {amount} {from_currency} → ${converted:.2f} USD (rate: {rate})")
        return round(converted, 2)
    else:
        # Unknown currency - log warning and return as-is
        logger.warning(f"⚠️ Unknown currency '{from_currency}' - returning amount as-is")
        return round(amount, 2)


def format_price_with_conversion(
    amount: float, 
    currency: str, 
    include_original: bool = True
) -> dict:
    """
    Convert a price to USD and return a formatted dict.
    
    Args:
        amount: Original amount
        currency: Original currency code
        include_original: Whether to include original price info
    
    Returns:
        Dict with USD price and optionally original currency info
    """
    usd_amount = convert_to_usd(amount, currency)
    
    result = {
        "price_usd": usd_amount,
        "currency": "USD"
    }
    
    if include_original and currency != "USD":
        result["original_price"] = round(amount, 2)
        result["original_currency"] = currency
    
    return result


# ============================================================================
# INITIALIZATION
# ============================================================================

def preload_rates():
    """
    Preload exchange rates at module initialization.
    Call this at server startup to ensure rates are cached.
    """
    logger.info("🔄 Preloading exchange rates...")
    rates = get_exchange_rates()
    logger.info(f"✅ Exchange rates ready ({len(rates)} currencies)")
    return rates


# Preload rates when module is imported
try:
    preload_rates()
except Exception as e:
    logger.warning(f"⚠️ Failed to preload rates at startup: {e}")

