"""
Nimeslug — Bilingual AI Assistant
Quick test: send a question, get a response.
"""

from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL, SYSTEM_PROMPT


def ask(question: str) -> str:
    """Send a question to Nimeslug and return the answer."""
    client = Groq(api_key=GROQ_API_KEY)
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        temperature=0.7,
        max_tokens=1024,
    )
    
    return response.choices[0].message.content


if __name__ == "__main__":
    print("🤖 Nimeslug starting...\n")
    
    # Test 1: Turkish
    tr_question = "Merhaba! Kendini tanıt ve enflasyon nedir kısaca anlat."
    print(f"👤 User (TR): {tr_question}\n")
    print(f"🤖 Nimeslug: {ask(tr_question)}\n")
    print("-" * 60 + "\n")
    
    # Test 2: English
    en_question = "Hello! Introduce yourself and briefly explain what inflation is."
    print(f"👤 User (EN): {en_question}\n")
    print(f"🤖 Nimeslug: {ask(en_question)}\n")