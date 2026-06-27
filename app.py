"""
Nimeslug — Streamlit Chat Interface with Tool Use & Charts
Bilingual (TR/EN) personal finance & economics AI assistant
with real-time market data and interactive visualizations.
"""

import json
import streamlit as st
from groq import Groq

from config import GROQ_API_KEY, LLM_MODEL, SYSTEM_PROMPT
from tools.market_data import (
    get_stock_price,
    get_forex_rate,
    get_crypto_price,
    get_price_history,
    get_crypto_history,
)
from tools.charts import create_price_chart, create_crypto_chart


# ─── Page Configuration ──────────────────────────────────────
st.set_page_config(
    page_title="Nimeslug — AI Finance Assistant",
    page_icon="🤖",
    layout="centered",
)


# Maximum recent messages to send to the API (keeps requests within TPM limits)
MAX_HISTORY_MESSAGES = 10


# ─── Tool Definitions for the LLM ────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_price",
            "description": (
                "Get the current price of a stock. Use for any stock or "
                "ETF query. For BIST (Turkish stocks), append '.IS' "
                "(e.g., 'THYAO.IS', 'ASELS.IS')."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol (e.g., 'AAPL', 'TSLA', 'THYAO.IS')",
                    }
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_forex_rate",
            "description": (
                "Get current forex exchange rate between two currencies. "
                "Use for any currency conversion or forex query."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pair": {
                        "type": "string",
                        "description": "Currency pair without slash (e.g., 'USDTRY', 'EURUSD', 'GBPTRY')",
                    }
                },
                "required": ["pair"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_crypto_price",
            "description": "Get current cryptocurrency price. Use for any crypto query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "coin_id": {
                        "type": "string",
                        "description": "CoinGecko coin ID in lowercase (e.g., 'bitcoin', 'ethereum', 'solana', 'cardano')",
                    },
                    "vs_currency": {
                        "type": "string",
                        "description": "Quote currency: 'usd', 'eur', or 'try'",
                        "default": "usd",
                    },
                },
                "required": ["coin_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_price_history",
            "description": (
                "Get historical price data for a stock or forex pair. "
                "Use when user asks about trends, charts, or past performance "
                "of stocks/forex. A chart will be displayed automatically. "
                "You receive only a summary (start/end price, % change, high/low) — "
                "the full price series is rendered as a chart to the user."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Symbol (forex needs '=X' suffix, e.g., 'USDTRY=X')",
                    },
                    "period": {
                        "type": "string",
                        "description": "Time period: '5d', '1mo', '3mo', '6mo', '1y', '5y'",
                        "default": "1mo",
                    },
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_crypto_history",
            "description": (
                "Get historical cryptocurrency price data. Use when user asks "
                "about crypto trends, past performance, or wants to see a chart. "
                "Always use this (NOT get_price_history) for crypto. A chart will "
                "be displayed automatically. You receive only a summary — the full "
                "price series is rendered as a chart to the user."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "coin_id": {
                        "type": "string",
                        "description": "CoinGecko ID lowercase (e.g., 'bitcoin', 'ethereum', 'solana')",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Days of history: 7, 14, 30, 90, 180, or 365",
                        "default": 30,
                    },
                    "vs_currency": {
                        "type": "string",
                        "description": "Quote currency: 'usd', 'eur', or 'try'",
                        "default": "usd",
                    },
                },
                "required": ["coin_id"],
            },
        },
    },
]


# Map tool names to actual functions
TOOL_FUNCTIONS = {
    "get_stock_price": get_stock_price,
    "get_forex_rate": get_forex_rate,
    "get_crypto_price": get_crypto_price,
    "get_price_history": get_price_history,
    "get_crypto_history": get_crypto_history,
}


# ─── Initialize Groq Client ──────────────────────────────────
@st.cache_resource
def get_client():
    return Groq(api_key=GROQ_API_KEY)


client = get_client()


# ─── Tool Execution Helper ───────────────────────────────────
def execute_tool(tool_call) -> tuple[str, dict]:
    """
    Run a tool call.
    
    Returns:
        (llm_payload, full_result)
        - llm_payload: compact JSON string sent BACK to the LLM (saves tokens)
        - full_result: complete dict kept for chart rendering
    """
    function_name = tool_call.function.name
    function_args = json.loads(tool_call.function.arguments)
    
    if function_name not in TOOL_FUNCTIONS:
        err = {"error": f"Unknown tool: {function_name}"}
        return json.dumps(err), err
    
    result = TOOL_FUNCTIONS[function_name](**function_args)
    
    # For heavy history tools, send only a compact summary to the LLM
    # (we keep the full data locally for chart rendering)
    if function_name == "get_crypto_history" and "error" not in result:
        compact = {
            "coin": result["coin"],
            "currency": result["currency"],
            "days": result["days"],
            "summary": result["summary"],
            "note": "Full price series omitted to save tokens; chart is rendered separately for the user.",
        }
        return json.dumps(compact, default=str), result
    
    if function_name == "get_price_history" and "error" not in result:
        prices = result.get("prices", [])
        dates = result.get("dates", [])
        if prices:
            start_price = prices[0]
            end_price = prices[-1]
            change_pct = ((end_price - start_price) / start_price) * 100 if start_price else 0
            compact = {
                "ticker": result["ticker"],
                "period": result["period"],
                "summary": {
                    "start_date": dates[0] if dates else None,
                    "end_date": dates[-1] if dates else None,
                    "start_price": round(start_price, 2),
                    "end_price": round(end_price, 2),
                    "change_pct": round(change_pct, 2),
                    "high": round(max(prices), 2),
                    "low": round(min(prices), 2),
                    "data_points": len(prices),
                },
                "note": "Full price series omitted to save tokens; chart is rendered separately for the user.",
            }
            return json.dumps(compact, default=str), result
    
    # For other tools (current price, forex), send full result (it's small)
    return json.dumps(result, default=str), result


# ─── Main Chat Function ──────────────────────────────────────
def chat_with_tools(messages: list, max_iterations: int = 5) -> tuple[str, list]:
    """
    Run a chat completion with a tool-use loop.
    
    The LLM may call multiple tools across several turns before composing
    a final answer. We loop up to `max_iterations` times to handle this.
    
    Returns:
        (final_answer, used_tools_info)
    """
    used_tools = []
    
    for iteration in range(max_iterations):
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.7,
            max_tokens=1024,
        )
        
        response_msg = response.choices[0].message
        
        # No tool call → we're done
        if not response_msg.tool_calls:
            return response_msg.content or "", used_tools
        
        # Add the assistant message containing the tool calls
        messages.append({
            "role": "assistant",
            "content": response_msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in response_msg.tool_calls
            ],
        })
        
        # Execute each tool call
        for tool_call in response_msg.tool_calls:
            llm_payload, full_result = execute_tool(tool_call)
            used_tools.append({
                "name": tool_call.function.name,
                "args": tool_call.function.arguments,
                "result": json.dumps(full_result, default=str),  # full data → for charts
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": llm_payload,  # compact data → for LLM
            })
    
    # Iteration limit reached: force a final summary without tools
    final_response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages
        + [
            {
                "role": "user",
                "content": (
                    "Please summarize the tool results above and provide "
                    "a final answer to the original question. Do not call "
                    "any more tools."
                ),
            }
        ],
        temperature=0.7,
        max_tokens=1024,
    )
    
    return final_response.choices[0].message.content or "", used_tools


# ─── Chart Builder ───────────────────────────────────────────
def build_charts_from_tools(used_tools: list) -> list:
    """
    Inspect used tools and build a Plotly figure for any history results.
    Returns a list of Plotly Figure objects (possibly empty).
    """
    charts = []
    for tool in used_tools:
        try:
            result = json.loads(tool["result"])
            if "error" in result:
                continue
            
            if tool["name"] == "get_price_history":
                charts.append(create_price_chart(result))
            
            elif tool["name"] == "get_crypto_history":
                charts.append(
                    create_crypto_chart(
                        coin_id=result["coin"],
                        prices_data=result["prices"],
                        currency=result["currency"],
                    )
                )
        except (json.JSONDecodeError, KeyError, TypeError):
            pass  # Skip malformed results silently
    
    return charts


# ─── UI ──────────────────────────────────────────────────────
st.title("🤖 Nimeslug")
st.caption("Your bilingual AI assistant for personal finance & economics — now with live market data")


# ─── Sidebar ─────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    st.markdown(f"**Model:** `{LLM_MODEL}`")
    st.markdown("**Language:** Auto (TR/EN)")
    st.markdown("**Tools:** 📈 Stocks · 💰 Forex · ₿ Crypto · 📊 Charts")
    st.markdown(f"**Context window:** Last {MAX_HISTORY_MESSAGES} messages")
    
    st.divider()
    
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    
    st.markdown("### 💡 Try asking")
    st.markdown(
        """
        - Apple hissesi ne durumda?
        - What's the Bitcoin price right now?
        - Dolar TL kuru kaç?
        - Bitcoin son 30 günü nasıl?
        - Show me Tesla's last 3 months
        - Compare Tesla and Apple this month
        - Enflasyon nedir kısaca anlat
        """
    )


# ─── Initialize Chat History ─────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []


# ─── Display Chat History ────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("charts"):
            for chart in msg["charts"]:
                st.plotly_chart(chart, use_container_width=True)


# ─── Chat Input ──────────────────────────────────────────────
if prompt := st.chat_input("Ask me anything about finance, markets, or economics..."):
    # Save and display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Build API message list (text-only history, limited to recent N)
            api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            recent_messages = st.session_state.messages[-MAX_HISTORY_MESSAGES:]
            for m in recent_messages:
                api_messages.append({"role": m["role"], "content": m["content"]})
            
            answer, used_tools = chat_with_tools(api_messages)
            st.markdown(answer)
            
            # Build and display any charts triggered by tools
            charts = build_charts_from_tools(used_tools)
            for chart in charts:
                st.plotly_chart(chart, use_container_width=True)
            
            # Show which tools were used (transparency)
            if used_tools:
                with st.expander(f"🔧 Used {len(used_tools)} tool(s)"):
                    for tool in used_tools:
                        st.markdown(f"**{tool['name']}**")
                        st.code(tool["args"], language="json")
    
    # Save the assistant's answer + any charts to history
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "charts": charts,
    })