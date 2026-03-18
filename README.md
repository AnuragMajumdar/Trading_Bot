# Binance Futures Testnet Trading Bot

A production-quality CLI trading bot for placing **MARKET** and **LIMIT** orders on the Binance Futures Testnet (USDT-M). Built with Python and the `python-binance` library.

> **This bot connects exclusively to the Binance Futures Testnet. No real funds are ever at risk.**

---

## Features

- **MARKET orders** — execute immediately at the current market price
- **LIMIT orders** — place at a specific price with GTC (Good Till Cancelled) time-in-force
- **BUY and SELL** support for both order types
- **Input validation** — symbol format, quote asset suffix, quantity/price parsing via `Decimal`
- **Automatic retry** — transient network failures retry up to 3 times with exponential backoff
- **Rotating file logs** — all activity logged with timestamps and severity levels
- **Structured CLI output** — clear success/failure messages in the terminal
- **No hardcoded secrets** — API keys loaded from a `.env` file

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # Package exports
│   ├── client.py            # Binance Futures Testnet client initialization
│   ├── orders.py            # Order placement logic with retry
│   ├── validators.py        # Input validation and decimal normalization
│   └── logging_config.py    # Rotating file + console logger setup
├── cli.py                   # CLI entry point (argparse)
├── requirements.txt         # Python dependencies
├── .env                     # API keys (you create this — not committed)
└── logs/
    └── trading_bot.log      # Auto-created at first run
```

---

## Setup Instructions

### 1. Get Binance Futures Testnet API Keys

1. Go to **https://testnet.binancefuture.com**
2. Click **Log In** and authenticate with your GitHub account
3. Once logged in, navigate to **API Key** in the bottom-left sidebar
4. You will see your **API Key** and **Secret Key** — copy both

> These are testnet-only credentials. They do not work on the real Binance exchange.

### 2. Clone or Navigate to the Project

```bash
cd trading_bot
```

### 3. Create a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Create the `.env` File

Create a file named `.env` in the `trading_bot/` root directory:

```
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_secret_key_here
```

Replace the placeholder values with the keys from Step 1.

> **Do not commit `.env` to version control.** Add it to your `.gitignore`.

---

## Usage

All commands are run from the `trading_bot/` directory with the virtual environment activated.

### Place a MARKET Order

```bash
python cli.py market --symbol BTCUSDT --side BUY --quantity 0.001
```

### Place a LIMIT Order

```bash
python cli.py limit --symbol ETHUSDT --side SELL --quantity 0.05 --price 3500.00
```

### CLI Help

```bash
python cli.py --help
python cli.py market --help
python cli.py limit --help
```

### Argument Reference

| Argument     | Required          | Description                          |
|-------------|-------------------|--------------------------------------|
| `--symbol`  | Yes               | Trading pair (e.g. `BTCUSDT`)        |
| `--side`    | Yes               | `BUY` or `SELL`                      |
| `--quantity`| Yes               | Order quantity (e.g. `0.001`)        |
| `--price`   | LIMIT orders only | Limit price (e.g. `65000.00`)        |

---

## Sample Output

### Successful MARKET Order

```
2026-03-18 19:50:01 | INFO     | trading_bot | Binance Futures Testnet client initialized. Server time: 1710791401000
2026-03-18 19:50:01 | INFO     | trading_bot | Placing MARKET BUY 0.001 BTCUSDT
2026-03-18 19:50:02 | INFO     | trading_bot | MARKET order filled — orderId=123456, symbol=BTCUSDT, side=BUY, qty=0.001, status=FILLED

  [SUCCESS] MARKET order placed
  Order ID : 123456
  Symbol   : BTCUSDT
  Side     : BUY
  Quantity : 0.001
  Status   : FILLED
  Avg Price: 84520.50
```

### Failed Validation

```
  [FAILED] Input validation
  Error: Invalid symbol: 'BTCXYZ'. Must end with a known quote asset: USDT, BUSD, BTC, ETH, BNB.
```

### Failed Order (API Error)

```
  [FAILED] Order placement
  Error: Binance API error: [-1121] Invalid symbol.
```

---

## Logging

- **Log file**: `logs/trading_bot.log`
- **Rotation**: 5 MB per file, 3 backup files retained
- **Format**: `YYYY-MM-DD HH:MM:SS | LEVEL | trading_bot | message`
- **Console**: INFO and above printed to stdout
- **File**: DEBUG and above written to log file
- The `logs/` directory is created automatically on first run

---

## Assumptions

1. **Testnet only** — the bot is hardcoded to use `https://testnet.binancefuture.com`. It will never connect to the live Binance API.
2. **USDT-M Futures** — designed for USDT-margined futures contracts (e.g. `BTCUSDT`, `ETHUSDT`).
3. **GTC time-in-force** — LIMIT orders use Good Till Cancelled. They remain open until filled or manually cancelled.
4. **No leverage management** — the bot places orders using whatever leverage is currently set on your testnet account (default 20x). Adjust leverage via the testnet web UI.
5. **Symbol validation** — accepted quote assets are `USDT`, `BUSD`, `BTC`, `ETH`, and `BNB`.
6. **Python 3.10+** — uses `str | None` union syntax in type hints.
7. **Single orders** — the bot places one order per CLI invocation. It is not a continuously running strategy bot.
