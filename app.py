"""
Nimeslug — Streamlit Chat Interface
Bilingual (TR/EN) personal finance & economics AI assistant.
"""

import streamlit as st
from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL, SYSTEM_PROMPT


# ─── Page Configuration ──────────────────────────────────────
st.set_page_config(
    page_title="Nimeslug — AI Finance Assistant",
    page_icon="🤖",
    layout="centered",
)


# ─── Initialize Groq Client (cached) ─────────────────────────
@st.cache_resource
def get_client():
    """Create Groq client once and cache it."""
    return Groq(api_key=GROQ_API_KEY)


client = get_client()


# ─── Header ──────────────────────────────────────────────────
st.title("🤖 Nimeslug")
st.caption("Your bilingual AI assistant for personal finance & economics")


# ─── Sidebar ─────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    
    st.markdown("**Model:** `llama-3.3-70b-versatile`")
    st.markdown("**Language:** Auto-detect (TR/EN)")
    
    st.divider()
    
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    
    st.markdown("### 💡 Example questions")
    st.markdown(
        """
        - Enflasyon nedir, kısaca anlat
        - What's the difference between stocks and bonds?
        - Faiz artışı ekonomiyi nasıl etkiler?
        - Explain compound interest with an example
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
if prompt := st.chat_input("Ask me anything about finance or economics..."):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate and display assistant response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Build messages list including system prompt and full history
            api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            api_messages.extend(st.session_state.messages)
            
            # Call Groq
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=api_messages,
                temperature=0.7,
                max_tokens=1024,
            )
            
            answer = response.choices[0].message.content
            st.markdown(answer)
    
    # Add assistant response to history
    st.session_state.messages.append({"role": "assistant", "content": answer})