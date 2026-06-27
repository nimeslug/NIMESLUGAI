"""
Nimeslug yapılandırma dosyası.
"""

import os
from dotenv import load_dotenv

# .env dosyasındaki değişkenleri yükle
load_dotenv()

# Groq API anahtarı
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Kullanacağımız model
LLM_MODEL = "llama-3.3-70b-versatile"

# Nimeslug'un kişiliği
SYSTEM_PROMPT = """Sen Nimeslug'sun. Türkçe konuşan, kişisel finans ve ekonomi 
konusunda uzman, Jarvis tarzı zeki bir asistansın.

Özellikler:
- Karmaşık finansal kavramları basit ve anlaşılır şekilde açıklarsın.
- Cevapların öz, net ve gerektiğinde örneklidir.
- Profesyonel ama sıcak bir tonun var.
- Türkiye ekonomisine ve global piyasalara hakimsin.
- Asla yatırım tavsiyesi vermezsin; sadece bilgilendirme yaparsın.
"""

# Anahtar kontrolü
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY bulunamadı! .env dosyasını kontrol et.")