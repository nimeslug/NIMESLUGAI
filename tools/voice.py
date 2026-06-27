"""
Voice tools for Nimeslug.
Speech-to-text via Groq Whisper API.
"""

import io
from groq import Groq
from config import GROQ_API_KEY


# Reuse a single client
_client = None


def get_client() -> Groq:
    """Get or create the Groq client (singleton)."""
    global _client
    if _client is None:
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


def transcribe_audio(audio_bytes: bytes, language: str = None) -> dict:
    """
    Transcribe audio bytes to text using Groq Whisper.
    
    Args:
        audio_bytes: Raw audio bytes (webm/wav/mp3/m4a from browser)
        language: Optional ISO-639-1 hint ('tr', 'en') — if None, auto-detect
    
    Returns:
        dict with 'text', 'language', and 'duration' (or 'error')
    """
    try:
        client = get_client()
        
        # Wrap bytes in a file-like object the API can read
        # The API needs a (filename, bytes, mimetype) tuple
        audio_file = ("audio.webm", audio_bytes, "audio/webm")
        
        # Whisper Large V3 Turbo — fast and accurate, supports 100+ languages
        kwargs = {
            "file": audio_file,
            "model": "whisper-large-v3-turbo",
            "response_format": "verbose_json",  # Includes language info
            "temperature": 0.0,  # Deterministic transcription
        }
        if language:
            kwargs["language"] = language
        
        result = client.audio.transcriptions.create(**kwargs)
        
        return {
            "text": result.text.strip(),
            "language": getattr(result, "language", "unknown"),
            "duration": getattr(result, "duration", None),
        }
    except Exception as e:
        return {"error": f"Transcription failed: {str(e)}"}


def detect_language(text: str) -> str:
    """
    Simple heuristic to detect language from text.
    Used to choose TTS voice on the browser side.
    
    Returns:
        'tr' if Turkish detected, otherwise 'en'
    """
    if not text:
        return "en"
    
    # Turkish-specific characters
    tr_chars = set("ğüşıöçĞÜŞİÖÇ")
    if any(c in tr_chars for c in text):
        return "tr"
    
    # Common Turkish words
    tr_words = {
        "bir", "bu", "ne", "ve", "için", "ile", "var", "yok",
        "ben", "sen", "biz", "siz", "şu", "çok", "az", "evet", "hayır",
        "nedir", "nasıl", "neden", "kaç", "kim",
    }
    text_lower = text.lower()
    words = set(text_lower.split())
    
    if len(words & tr_words) >= 2:
        return "tr"
    
    return "en"


# ─── Quick Test ──────────────────────────────────────────────
if __name__ == "__main__":
    print("Voice module loaded successfully.")
    print(f"Language detection test:")
    print(f"  'Merhaba nasılsın?' → {detect_language('Merhaba nasılsın?')}")
    print(f"  'Hello, how are you?' → {detect_language('Hello, how are you?')}")