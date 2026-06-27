"""
Market data tools for Nimeslug.
Fetches real-time prices and historical data for stocks, crypto, and forex.
"""

import yfinance as yf
from pycoingecko import CoinGeckoAPI
from datetime import datetime


# CoinGecko client (no API key needed for free tier)
cg = CoinGeckoAPI()


# ─── STOCKS & FOREX (via Yahoo Finance) ──────────────────────

def get_stock_price(ticker: str) -> dict:
    """Get current stock price and basic info."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        history = stock.history(period="2d")
        
        if history.empty:
            return {"error": f"No data found for ticker '{ticker}'"}
        
        current_price = history["Close"].iloc[-1]
        previous_close = history["Close"].iloc[-2] if len(history) > 1 else current_price
        change = current_price - previous_close
        change_pct = (change / previous_close) * 100 if previous_close else 0
        
        return {
            "ticker": ticker.upper(),
            "name": info.get("longName", ticker),
            "price": round(float(current_price), 2),
            "change": round(float(change), 2),
            "change_pct": round(float(change_pct), 2),
            "currency": info.get("currency", "USD"),
            "market_cap": info.get("marketCap"),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        return {"error": f"Failed to fetch '{ticker}': {str(e)}"}


def get_forex_rate(pair: str) -> dict:
    """Get forex exchange rate."""
    ticker = f"{pair.upper()}=X"
    result = get_stock_price(ticker)
    
    if "error" not in result:
        result["pair"] = pair.upper()
        result["type"] = "forex"
    
    return result


# ─── CRYPTO (via CoinGecko) ──────────────────────────────────

def get_crypto_price(coin_id: str, vs_currency: str = "usd") -> dict:
    """Get current cryptocurrency price."""
    try:
        data = cg.get_price(
            ids=coin_id.lower(),
            vs_currencies=vs_currency.lower(),
            include_market_cap=True,
            include_24hr_change=True,
            include_24hr_vol=True,
        )
        
        if not data or coin_id.lower() not in data:
            return {"error": f"Crypto '{coin_id}' not found"}
        
        coin_data = data[coin_id.lower()]
        currency = vs_currency.lower()
        
        return {
            "coin": coin_id.lower(),
            "price": coin_data.get(currency),
            "currency": currency.upper(),
            "change_24h_pct": round(coin_data.get(f"{currency}_24h_change", 0), 2),
            "market_cap": coin_data.get(f"{currency}_market_cap"),
            "volume_24h": coin_data.get(f"{currency}_24h_vol"),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        return {"error": f"Failed to fetch crypto '{coin_id}': {str(e)}"}


def get_crypto_history(coin_id: str, days: int = 30, vs_currency: str = "usd") -> dict:
    """
    Get historical cryptocurrency price data for charting.
    
    Args:
        coin_id: CoinGecko ID (e.g., 'bitcoin', 'ethereum', 'solana')
        days: Number of days back (1, 7, 14, 30, 90, 180, 365)
        vs_currency: Quote currency ('usd', 'eur', 'try')
    
    Returns:
        dict with raw [timestamp_ms, price] pairs and summary metadata
    """
    try:
        data = cg.get_coin_market_chart_by_id(
            id=coin_id.lower(),
            vs_currency=vs_currency.lower(),
            days=days,
        )
        
        if not data or "prices" not in data or not data["prices"]:
            return {"error": f"No history found for '{coin_id}'"}
        
        prices = data["prices"]  # list of [timestamp_ms, price]
        start_price = prices[0][1]
        end_price = prices[-1][1]
        change_pct = ((end_price - start_price) / start_price) * 100 if start_price else 0
        
        return {
            "coin": coin_id.lower(),
            "currency": vs_currency.upper(),
            "days": days,
            "prices": prices,
            "summary": {
                "start_price": round(start_price, 2),
                "end_price": round(end_price, 2),
                "change_pct": round(change_pct, 2),
                "data_points": len(prices),
            },
        }
    except Exception as e:
        return {"error": f"Failed to fetch crypto history: {str(e)}"}


# ─── HISTORICAL DATA (for stocks/forex charts) ───────────────

def get_price_history(ticker: str, period: str = "1mo") -> dict:
    """
    Get historical price data for charting.
    
    Args:
        ticker: Stock/forex symbol (use '=X' suffix for forex like 'USDTRY=X')
        period: '1d', '5d', '1mo', '3mo', '6mo', '1y', '5y', 'max'
    
    Returns:
        dict with dates and prices, or error
    """
    try:
        data = yf.Ticker(ticker).history(period=period)
        
        if data.empty:
            return {"error": f"No history for '{ticker}'"}
        
        return {
            "ticker": ticker.upper(),
            "dates": data.index.strftime("%Y-%m-%d").tolist(),
            "prices": data["Close"].round(2).tolist(),
            "volumes": data["Volume"].tolist(),
            "period": period,
        }
    except Exception as e:
        return {"error": f"Failed to fetch history: {str(e)}"}


# ─── QUICK TEST ──────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing market data tools...\n")
    
    print("📈 Apple stock:")
    print(get_stock_price("AAPL"), "\n")
    
    print("💰 USD/TRY:")
    print(get_forex_rate("USDTRY"), "\n")
    
    print("₿ Bitcoin:")
    print(get_crypto_price("bitcoin", "usd"), "\n")
    
    print("📊 Tesla 1-month history (first 5 days):")
    history = get_price_history("TSLA", "1mo")
    if "error" not in history:
        print(f"Ticker: {history['ticker']}")
        for date, price in zip(history["dates"][:5], history["prices"][:5]):
            print(f"  {date}: ${price}")
    print()
    
    print("📈 Bitcoin 30-day history (summary):")
    btc_history = get_crypto_history("bitcoin", days=30)
    if "error" not in btc_history:
        s = btc_history["summary"]
        print(f"  Start: ${s['start_price']} → End: ${s['end_price']}")
        print(f"  Change: {s['change_pct']:+.2f}%  ({s['data_points']} data points)")
    else:
        print(f"  Error: {btc_history['error']}")