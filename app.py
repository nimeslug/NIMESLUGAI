"""
Nimeslug — Streamlit Chat Interface with Tool Use, Charts, RAG, Voice & Budget
Bilingual (TR/EN) personal finance & economics AI assistant with:
- Real-time market data
- Interactive visualizations
- Personal knowledge base (RAG)
- Voice interaction (Jarvis mode)
- Personal budget tracking
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
from tools.charts import (
    create_price_chart,
    create_crypto_chart,
    create_category_pie_chart,
    create_category_bar_chart,
)
from tools.rag import (
    search_knowledge_base,
    index_all_pdfs,
    get_kb_stats,
    clear_knowledge_base,
    KNOWLEDGE_BASE_DIR,
)
from tools.voice import transcribe_audio, detect_language
from tools.budget import (
    add_transaction,
    get_summary,
    get_all_transactions,
    delete_transaction,
    clear_all_transactions,
    CATEGORIES,
)


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
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": (
                "Search the user's personal knowledge base of finance and economics "
                "documents (books, papers, articles they uploaded). Use this when the "
                "user asks about specific concepts, theories, authors, or wants insight "
                "based on their own reference material. Always cite the source document "
                "and page in your answer (e.g., 'According to filename.pdf page X...')."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query — what concept or question to look up",
                    },
                    "n_results": {
                        "type": "integer",
                        "description": "Number of top results (default 4)",
                        "default": 4,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_transaction",
            "description": (
                "Record a new financial transaction (expense or income) in the user's "
                "personal budget tracker. Use this when the user mentions spending money "
                "or receiving income (e.g., 'Bugün markete 450 TL harcadım', 'I spent $20 "
                "on coffee', 'Maaşım 25000 TL geldi'). Extract the amount, infer the "
                "category, and confirm the recording in your response."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "Transaction amount (positive number)",
                    },
                    "category": {
                        "type": "string",
                        "description": (
                            f"Category. Use one of: {', '.join(CATEGORIES)}. "
                            "Pick the closest match based on the description."
                        ),
                    },
                    "description": {
                        "type": "string",
                        "description": "Brief description of what the transaction was for",
                    },
                    "currency": {
                        "type": "string",
                        "description": "Currency code: TRY, USD, EUR (default TRY)",
                        "default": "TRY",
                    },
                    "transaction_type": {
                        "type": "string",
                        "description": "'expense' or 'income'",
                        "default": "expense",
                    },
                },
                "required": ["amount", "category"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_summary",
            "description": (
                "Get a summary of the user's budget for a given period. Returns totals, "
                "category breakdown, and recent transactions. Use when the user asks "
                "about their spending, e.g., 'Bu ay ne kadar harcadım?', 'Show my "
                "weekly summary', 'En çok hangi kategoride harcıyorum?'. A pie chart "
                "is rendered automatically when category data is available."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "description": (
                            "Time window: 'today', 'week', 'month', 'year', 'all'. "
                            "Default 'month'."
                        ),
                        "default": "month",
                    },
                },
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
    "search_knowledge_base": search_knowledge_base,
    "add_transaction": add_transaction,
    "get_summary": get_summary,
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
    
    # For other tools, send full result
    return json.dumps(result, default=str), result


# ─── Main Chat Function ──────────────────────────────────────
def chat_with_tools(messages: list, max_iterations: int = 5) -> tuple[str, list]:
    """Run a chat completion with a tool-use loop."""
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
        
        if not response_msg.tool_calls:
            return response_msg.content or "", used_tools
        
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
        
        for tool_call in response_msg.tool_calls:
            llm_payload, full_result = execute_tool(tool_call)
            used_tools.append({
                "name": tool_call.function.name,
                "args": tool_call.function.arguments,
                "result": json.dumps(full_result, default=str),
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": llm_payload,
            })
    
    # Iteration limit reached: force a final summary
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


# ─── Browser TTS Helper ──────────────────────────────────────
def speak_in_browser(text: str, lang: str = "en") -> None:
    """Use the browser's speechSynthesis API to read text aloud."""
    safe_text = (
        text.replace("\\", "\\\\")
        .replace("`", "\\`")
        .replace("\n", " ")
        .replace("\r", " ")
    )
    voice_lang = "tr-TR" if lang == "tr" else "en-US"
    
    import uuid
    component_id = f"tts-{uuid.uuid4().hex[:8]}"
    
    html = f"""
    <div id="{component_id}"></div>
    <script>
        (function() {{
            if (!window.speechSynthesis) return;
            window.speechSynthesis.cancel();
            
            const utterance = new SpeechSynthesisUtterance(`{safe_text}`);
            utterance.lang = "{voice_lang}";
            utterance.rate = 1.0;
            utterance.pitch = 1.0;
            utterance.volume = 1.0;
            
            const voices = window.speechSynthesis.getVoices();
            const match = voices.find(v => v.lang.startsWith("{voice_lang}".substring(0, 2)));
            if (match) utterance.voice = match;
            
            window.speechSynthesis.speak(utterance);
        }})();
    </script>
    """
    st.components.v1.html(html, height=0)


# ─── Chart Builder ───────────────────────────────────────────
def build_charts_from_tools(used_tools: list) -> list:
    """Build Plotly figures for any tool results that warrant a chart."""
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
            
            elif tool["name"] == "get_summary":
                by_category = result.get("by_category", {})
                if by_category:
                    period_label = result.get("period", "month").capitalize()
                    charts.append(
                        create_category_pie_chart(
                            by_category,
                            title=f"{period_label} — Spending by Category",
                        )
                    )
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    
    return charts


# ─── UI ──────────────────────────────────────────────────────
st.title("🤖 Nimeslug")
st.caption("Your bilingual AI assistant for personal finance & economics — with market data, knowledge base, voice, and budget tracking")


# ─── Sidebar ─────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    st.markdown(f"**Model:** `{LLM_MODEL}`")
    st.markdown("**Language:** Auto (TR/EN)")
    st.markdown("**Tools:** 📈 Stocks · 💰 Forex · ₿ Crypto · 📊 Charts · 📚 RAG · 🎙️ Voice · 💸 Budget")
    st.markdown(f"**Context window:** Last {MAX_HISTORY_MESSAGES} messages")
    
    st.divider()
    
    # ─── Voice Mode ─────────────────────────────────────
    st.markdown("### 🎙️ Voice Mode")
    
    if "voice_mode" not in st.session_state:
        st.session_state.voice_mode = False
    
    st.session_state.voice_mode = st.toggle(
        "Enable voice output (TTS)",
        value=st.session_state.voice_mode,
        help="Reads Nimeslug's responses aloud using your browser's voice.",
    )
    
    st.caption("💡 Speak by clicking the 🎤 button below the chat input")
    
    st.divider()
    
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    
    # ─── Budget Management ──────────────────────────────
    st.markdown("### 💰 Budget")
    
    summary = get_summary("month")
    if "error" not in summary and summary.get("transaction_count", 0) > 0:
        exp = summary["total_expense"]
        inc = summary["total_income"]
        net = summary["net"]
        net_emoji = "💚" if net >= 0 else "❤️"
        st.markdown(
            f"**This month:**  \n"
            f"📤 Expense: `{exp:,.2f} TRY`  \n"
            f"📥 Income: `{inc:,.2f} TRY`  \n"
            f"{net_emoji} Net: `{net:,.2f} TRY`"
        )
        st.caption(f"{summary['transaction_count']} transaction(s) this month")
    else:
        st.info("No transactions yet. Tell Nimeslug what you spent!")
    
    if st.button("🗑️ Clear all budget data", use_container_width=True):
        clear_all_transactions()
        st.success("Budget cleared")
        st.rerun()
    
    st.divider()
    
    # ─── Knowledge Base Management ──────────────────────
    st.markdown("### 📚 Knowledge Base")
    
    stats = get_kb_stats()
    if stats.get("total_chunks", 0) > 0:
        st.success(
            f"📖 {stats['total_sources']} document(s) · "
            f"{stats['total_chunks']} chunks indexed"
        )
        with st.expander("📂 Sources"):
            for src in stats.get("sources", []):
                st.markdown(f"- `{src}`")
    else:
        st.info(
            f"No documents indexed yet. Drop PDFs into the "
            f"`{KNOWLEDGE_BASE_DIR}/` folder and click Re-index."
        )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Re-index", use_container_width=True):
            with st.spinner("Indexing PDFs..."):
                results = index_all_pdfs()
                if not results:
                    st.warning("No PDFs found in knowledge_base/")
                else:
                    for r in results:
                        if "error" in r:
                            st.error(f"❌ {r['error']}")
                        else:
                            st.success(
                                f"✅ {r['file']} ({r['pages']}p, {r['chunks']} chunks)"
                            )
            st.rerun()
    
    with col2:
        if st.button("🗑️ Clear KB", use_container_width=True):
            clear_knowledge_base()
            st.success("Knowledge base cleared")
            st.rerun()
    
    st.divider()
    
    st.markdown("### 💡 Try asking")
    st.markdown(
        """
        - Apple hissesi ne durumda?
        - What's the Bitcoin price right now?
        - Dolar TL kuru kaç?
        - Bitcoin son 30 günü nasıl?
        - Bugün markete 450 TL harcadım
        - Maaşım 25000 TL geldi
        - Bu ay ne kadar harcadım?
        - Show my weekly budget summary
        - Yüklediğim dokümanda enflasyon nasıl tanımlanıyor?
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


# ─── Voice Input (Mic) ───────────────────────────────────────
st.markdown("##### 🎤 Or speak your question")
audio_value = st.audio_input(
    "Tap to record",
    label_visibility="collapsed",
    key="voice_recorder",
)

# If a new recording arrived, transcribe and inject it as a prompt
voice_prompt = None
if audio_value is not None:
    audio_bytes = audio_value.getvalue()
    if audio_bytes and audio_bytes != st.session_state.get("last_audio_bytes"):
        st.session_state.last_audio_bytes = audio_bytes
        with st.spinner("🎙️ Transcribing..."):
            transcription = transcribe_audio(audio_bytes)
        
        if "error" in transcription:
            st.error(f"❌ {transcription['error']}")
        elif transcription.get("text"):
            voice_prompt = transcription["text"]
            st.success(f"🎤 You said: *{voice_prompt}*")
        else:
            st.warning("Couldn't understand the audio. Try again?")


# ─── Chat Input ──────────────────────────────────────────────
text_prompt = st.chat_input("Ask me anything about finance, markets, or economics...")

# Use either voice or text input (whichever just arrived)
prompt = voice_prompt or text_prompt

if prompt:
    # Save and display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
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
            
            # Speak the response if voice mode is on
            if st.session_state.get("voice_mode"):
                speak_in_browser(answer, lang=detect_language(answer))
    
    # Save the assistant's answer + any charts to history
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "charts": charts,
    })