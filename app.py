"""
Nimeslug — Streamlit Chat Interface with Tool Use
Bilingual (TR/EN) personal finance & economics AI assistant
with real-time market data.
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
)


# ─── Page Configuration ──────────────────────────────────────
st.set_page_config(
    page_title="Nimeslug — AI Finance Assistant",
    page_icon="🤖",
    layout="centered",
)


# ─── Tool Definitions for the LLM ────────────────────────────
# We describe each tool so the LLM knows when/how to use it.
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
                "Useful for trend analysis or when user asks about past performance."
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
]


# Map tool names to actual functions
TOOL_FUNCTIONS = {
    "get_stock_price": get_stock_price,
    "get_forex_rate": get_forex_rate,
    "get_crypto_price": get_crypto_price,
    "get_price_history": get_price_history,
}


# ─── Initialize Groq Client ──────────────────────────────────
@st.cache_resource
def get_client():
    return Groq(api_key=GROQ_API_KEY)


client = get_client()


# ─── Tool Execution Helper ───────────────────────────────────
def execute_tool(tool_call) -> str:
    """Run a tool call and return JSON result."""
    function_name = tool_call.function.name
    function_args = json.loads(tool_call.function.arguments)
    
    if function_name not in TOOL_FUNCTIONS:
        return json.dumps({"error": f"Unknown tool: {function_name}"})
    
    result = TOOL_FUNCTIONS[function_name](**function_args)
    return json.dumps(result, default=str)


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
        # Call the model; always pass tools so it CAN call them if needed
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.7,
            max_tokens=1024,
        )
        
        response_msg = response.choices[0].message
        
        # If the model didn't call any tools, we're done — return the answer
        if not response_msg.tool_calls:
            return response_msg.content or "", used_tools
        
        # The model called one or more tools. Add its assistant message
        # (containing the tool_calls) to the conversation history.
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
        
        # Execute each tool call and append its result to the conversation
        for tool_call in response_msg.tool_calls:
            result = execute_tool(tool_call)
            used_tools.append({
                "name": tool_call.function.name,
                "args": tool_call.function.arguments,
                "result": result,
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })
        
        # Loop again — let the model see the tool results and decide:
        # either call more tools, or compose the final answer.
    
    # If we hit the iteration limit, force a final answer without tools
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


# ─── UI ──────────────────────────────────────────────────────
st.title("🤖 Nimeslug")
st.caption("Your bilingual AI assistant for personal finance & economics — now with live market data")


# ─── Sidebar ─────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    st.markdown("**Model:** `llama-3.3-70b-versatile`")
    st.markdown("**Language:** Auto (TR/EN)")
    st.markdown("**Tools:** 📈 Stocks · 💰 Forex · ₿ Crypto · 📊 History")
    
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
        - Compare Tesla and Apple performance this month
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


# ─── Chat Input ──────────────────────────────────────────────
if prompt := st.chat_input("Ask me anything about finance, markets, or economics..."):
    # Save and display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Build full message list for the API
            api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            api_messages.extend(st.session_state.messages)
            
            answer, used_tools = chat_with_tools(api_messages)
            st.markdown(answer)
            
            # Show which tools were used (transparency)
            if used_tools:
                with st.expander(f"🔧 Used {len(used_tools)} tool(s)"):
                    for tool in used_tools:
                        st.markdown(f"**{tool['name']}**")
                        st.code(tool["args"], language="json")
    
    # Save the assistant's final answer to chat history
    st.session_state.messages.append({"role": "assistant", "content": answer})