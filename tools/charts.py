"""
Chart generation tools for Nimeslug.
Creates interactive Plotly charts from historical market data.
"""

import plotly.graph_objects as go
from datetime import datetime


def create_price_chart(history_data: dict, title_override: str = None) -> go.Figure:
    """
    Build an interactive price chart from historical data.
    
    Args:
        history_data: dict from get_price_history() with keys 'dates', 'prices', 'ticker'
        title_override: Optional custom title
    
    Returns:
        Plotly Figure object ready to render in Streamlit
    """
    dates = history_data["dates"]
    prices = history_data["prices"]
    ticker = history_data["ticker"]
    period = history_data.get("period", "")
    
    # Determine line color based on overall trend
    start_price = prices[0]
    end_price = prices[-1]
    is_positive = end_price >= start_price
    line_color = "#26a69a" if is_positive else "#ef5350"  # green or red
    fill_color = "rgba(38, 166, 154, 0.1)" if is_positive else "rgba(239, 83, 80, 0.1)"
    
    # Build figure
    fig = go.Figure()
    
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=prices,
            mode="lines",
            name=ticker,
            line=dict(color=line_color, width=2.5),
            fill="tozeroy",
            fillcolor=fill_color,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Price: %{y:,.2f}"
                "<extra></extra>"
            ),
        )
    )
    
    # Calculate change for title
    change = end_price - start_price
    change_pct = (change / start_price) * 100 if start_price else 0
    change_symbol = "▲" if is_positive else "▼"
    
    title = title_override or (
        f"<b>{ticker}</b> — {period}  "
        f"<span style='color:{line_color}'>"
        f"{change_symbol} {abs(change_pct):.2f}%"
        f"</span>"
    )
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=18)),
        xaxis=dict(
            title=None,
            showgrid=True,
            gridcolor="rgba(128,128,128,0.15)",
            rangeslider=dict(visible=False),
        ),
        yaxis=dict(
            title="Price",
            showgrid=True,
            gridcolor="rgba(128,128,128,0.15)",
            tickformat=",.2f",
        ),
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=60, b=10),
        height=400,
        showlegend=False,
    )
    
    return fig


def create_crypto_chart(coin_id: str, prices_data: list, currency: str = "USD") -> go.Figure:
    """
    Build a chart for cryptocurrency historical data (from CoinGecko format).
    
    Args:
        coin_id: Crypto ID (e.g., 'bitcoin')
        prices_data: list of [timestamp_ms, price] pairs from CoinGecko
        currency: Quote currency for display
    
    Returns:
        Plotly Figure
    """
    if not prices_data:
        # Empty chart with a friendly message
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16),
        )
        return fig
    
    dates = [datetime.fromtimestamp(p[0] / 1000).strftime("%Y-%m-%d") for p in prices_data]
    prices = [p[1] for p in prices_data]
    
    history_data = {
        "dates": dates,
        "prices": prices,
        "ticker": coin_id.upper(),
        "period": f"{len(prices)} days",
    }
    
    return create_price_chart(history_data)