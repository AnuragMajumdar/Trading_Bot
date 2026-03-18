import os
import logging

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from dotenv import load_dotenv

logger = logging.getLogger("trading_bot")

FUTURES_TESTNET_BASE_URL = "https://testnet.binancefuture.com"


class ClientError(Exception):
    """Raised when the Binance client cannot be initialized."""
    pass


def get_futures_client() -> Client:
    """
    Load API credentials from .env file and return a configured
    Binance client pointed at the Futures Testnet.
    Verifies connectivity with a server ping before returning.
    """
    load_dotenv()

    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")

    if not api_key or not api_secret:
        raise ClientError(
            "Missing API credentials. Set BINANCE_API_KEY and BINANCE_API_SECRET in your .env file."
        )

    try:
        client = Client(api_key, api_secret, testnet=True)
        # Override base URL to Futures Testnet
        client.FUTURES_URL = FUTURES_TESTNET_BASE_URL + "/fapi"

        # Verify we can reach the testnet and that credentials are valid
        client.futures_ping()
        server_time = client.futures_time()
        logger.info(
            "Binance Futures Testnet client initialized. Server time: %s",
            server_time.get("serverTime"),
        )
        return client
    except BinanceAPIException as exc:
        raise ClientError(
            f"Binance API rejected credentials: [{exc.code}] {exc.message}"
        ) from exc
    except BinanceRequestException as exc:
        raise ClientError(f"Network error reaching Binance Testnet: {exc}") from exc
    except (ConnectionError, TimeoutError, OSError) as exc:
        raise ClientError(
            f"Cannot connect to Binance Futures Testnet at {FUTURES_TESTNET_BASE_URL}: {exc}"
        ) from exc
    except Exception as exc:
        raise ClientError(f"Unexpected error during client init: {exc}") from exc
