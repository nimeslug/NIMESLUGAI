from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL, SYSTEM_PROMPT


def soru_sor(soru: str) -> str:
    """Nimeslug'a soru sorar, cevabı döndürür."""
    client = Groq(api_key=GROQ_API_KEY)
    
    mesajlar = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": soru},
    ]
    
    cevap = client.chat.completions.create(
        model=LLM_MODEL,
        messages=mesajlar,
        temperature=0.7,
        max_tokens=1024,
    )
    
    return cevap.choices[0].message.content


if __name__ == "__main__":
    print("🤖 Nimeslug başlatılıyor...\n")
    
    test_sorusu = "Merhaba Nimeslug! Kendini tanıt ve enflasyon nedir kısaca anlat."
    
    print(f"👤 Sen: {test_sorusu}\n")
    print("🤖 Nimeslug düşünüyor...\n")
    
    cevap = soru_sor(test_sorusu)
    
    print(f"🤖 Nimeslug: {cevap}\n")