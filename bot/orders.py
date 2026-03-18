import logging
import time

from binance.client import Client
from binance.enums import (
    SIDE_BUY,
    SIDE_SELL,
    TIME_IN_FORCE_GTC,
    FUTURE_ORDER_TYPE_MARKET,
    FUTURE_ORDER_TYPE_LIMIT,
)
from binance.exceptions import BinanceAPIException, BinanceRequestException

logger = logging.getLogger("trading_bot")

SIDE_MAP = {"BUY": SIDE_BUY, "SELL": SIDE_SELL}

# Retry config for transient network failures
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 1.5  # seconds, doubles each attempt


class OrderError(Exception):
    """Raised when an order placement fails."""
    pass


def _is_retryable(exc: Exception) -> bool:
    """Return True if the exception is a transient network issue worth retrying."""
    if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
        return True
    if isinstance(exc, BinanceRequestException):
        return True
    # Binance rate-limit (HTTP 429) or server error (5xx)
    if isinstance(exc, BinanceAPIException) and exc.code in (-1003, -1015):
        return True
    return False


def _execute_with_retry(order_fn, order_desc: str) -> dict:
    """
    Execute an order function with retry logic for transient failures.
    Non-retryable errors are raised immediately.
    """
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return order_fn()
        except Exception as exc:
            last_exc = exc
            if not _is_retryable(exc) or attempt == MAX_RETRIES:
                break
            wait = RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
            logger.warning(
                "%s failed (attempt %d/%d): %s — retrying in %.1fs",
                order_desc, attempt, MAX_RETRIES, exc, wait,
            )
            time.sleep(wait)

    # Convert to OrderError with context
    if isinstance(last_exc, BinanceAPIException):
        raise OrderError(
            f"Binance API error: [{last_exc.code}] {last_exc.message}"
        ) from last_exc
    if isinstance(last_exc, BinanceRequestException):
        raise OrderError(
            f"Network error after {MAX_RETRIES} attempts: {last_exc}"
        ) from last_exc
    if isinstance(last_exc, (ConnectionError, TimeoutError, OSError)):
        raise OrderError(
            f"Connection failed after {MAX_RETRIES} attempts: {last_exc}"
        ) from last_exc
    raise OrderError(f"Unexpected error: {last_exc}") from last_exc


def place_market_order(client: Client, symbol: str, side: str, quantity: str) -> dict:
    """
    Place a MARKET order on Binance Futures Testnet.
    Returns the API response dict on success.
    """
    desc = f"MARKET {side} {quantity} {symbol}"
    logger.info("Placing %s", desc)

    def _do_order():
        return client.futures_create_order(
            symbol=symbol,
            side=SIDE_MAP[side],
            type=FUTURE_ORDER_TYPE_MARKET,
            quantity=quantity,
        )

    response = _execute_with_retry(_do_order, desc)
    logger.info(
        "MARKET order filled — orderId=%s, symbol=%s, side=%s, qty=%s, status=%s",
        response.get("orderId"), symbol, side, quantity, response.get("status"),
    )
    return response


def place_limit_order(
    client: Client, symbol: str, side: str, quantity: str, price: str
) -> dict:
    """
    Place a LIMIT GTC order on Binance Futures Testnet.
    Returns the API response dict on success.
    """
    desc = f"LIMIT {side} {quantity} {symbol} @ {price}"
    logger.info("Placing %s", desc)

    def _do_order():
        return client.futures_create_order(
            symbol=symbol,
            side=SIDE_MAP[side],
            type=FUTURE_ORDER_TYPE_LIMIT,
            quantity=quantity,
            price=price,
            timeInForce=TIME_IN_FORCE_GTC,
        )

    response = _execute_with_retry(_do_order, desc)
    logger.info(
        "LIMIT order accepted — orderId=%s, symbol=%s, side=%s, qty=%s, price=%s, status=%s",
        response.get("orderId"), symbol, side, quantity, price, response.get("status"),
    )
    return response
