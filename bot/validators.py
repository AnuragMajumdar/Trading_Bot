import logging
from decimal import Decimal, InvalidOperation

logger = logging.getLogger("trading_bot")

VALID_SIDES = ("BUY", "SELL")
VALID_ORDER_TYPES = ("MARKET", "LIMIT", "STOP_LIMIT")
KNOWN_QUOTE_ASSETS = ("USDT", "BUSD", "BTC", "ETH", "BNB")
MIN_SYMBOL_LENGTH = 5


class ValidationError(Exception):
    """Raised when order parameters fail validation."""
    pass


def _normalize_decimal(value: Decimal) -> str:
    """
    Convert a Decimal to a float-compatible string that Binance accepts.
    Strips trailing zeros and avoids scientific notation.
    e.g. Decimal('0.00100000') -> '0.001', Decimal('3500.00') -> '3500'
    """
    normalized = value.normalize()
    text = str(normalized)
    if "E" in text or "e" in text:
        text = f"{normalized:f}"
    return text


def _parse_positive_decimal(raw: str, field_name: str) -> Decimal:
    """Parse a string into a positive Decimal or raise ValidationError."""
    try:
        value = Decimal(raw)
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError(f"Invalid {field_name}: '{raw}'. Must be a positive number.")
    if value <= 0:
        raise ValidationError(f"{field_name.capitalize()} must be positive, got {value}.")
    return value


def validate_order_params(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: str | None = None,
    stop_price: str | None = None,
) -> dict:
    """
    Validate and normalize order parameters.
    Returns a dict with cleaned values ready for the API call.
    Raises ValidationError on any invalid input.
    """
    # Symbol: must be alphanumeric, reasonable length, end with a known quote asset
    if not symbol or not symbol.isalnum():
        raise ValidationError(f"Invalid symbol: '{symbol}'. Must be alphanumeric (e.g. BTCUSDT).")
    symbol = symbol.upper()
    if len(symbol) < MIN_SYMBOL_LENGTH:
        raise ValidationError(
            f"Invalid symbol: '{symbol}'. Too short — expected a pair like BTCUSDT."
        )
    if not any(symbol.endswith(quote) for quote in KNOWN_QUOTE_ASSETS):
        raise ValidationError(
            f"Invalid symbol: '{symbol}'. Must end with a known quote asset: "
            f"{', '.join(KNOWN_QUOTE_ASSETS)}."
        )

    # Side
    side = side.upper()
    if side not in VALID_SIDES:
        raise ValidationError(f"Invalid side: '{side}'. Must be one of {VALID_SIDES}.")

    # Order type
    order_type = order_type.upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(f"Invalid order type: '{order_type}'. Must be one of {VALID_ORDER_TYPES}.")

    # Quantity
    qty = _parse_positive_decimal(quantity, "quantity")

    # Price: required for LIMIT and STOP_LIMIT orders
    cleaned_price = None
    if order_type in ("LIMIT", "STOP_LIMIT"):
        if price is None:
            raise ValidationError(f"Price is required for {order_type} orders.")
        cleaned_price = _parse_positive_decimal(price, "price")

    # Stop price: required only for STOP_LIMIT orders
    cleaned_stop_price = None
    if order_type == "STOP_LIMIT":
        if stop_price is None:
            raise ValidationError("Stop price (--stop-price) is required for STOP_LIMIT orders.")
        cleaned_stop_price = _parse_positive_decimal(stop_price, "stop price")

    params = {
        "symbol": symbol,
        "side": side,
        "order_type": order_type,
        "quantity": _normalize_decimal(qty),
    }
    if cleaned_price is not None:
        params["price"] = _normalize_decimal(cleaned_price)
    if cleaned_stop_price is not None:
        params["stop_price"] = _normalize_decimal(cleaned_stop_price)

    logger.debug("Validated order params: %s", params)
    return params
