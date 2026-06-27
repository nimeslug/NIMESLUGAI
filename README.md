# 🤖 Nimeslug

A bilingual (Turkish & English) personal AI assistant specialized in personal finance and economics. Powered by Llama 3.3 70B via Groq.

## ✨ Features

- 🌍 **Bilingual** — Responds in Turkish or English based on user input
- 💰 **Finance expert** — Personal finance, budgeting, investing concepts
- 📊 **Economics tutor** — Inflation, interest rates, monetary policy
- 🎙️ **Voice-enabled** *(coming soon)* — Jarvis-style voice interaction
- 📈 **Market data** *(coming soon)* — Real-time stocks, crypto, forex
- 🧠 **Memory** *(coming soon)* — Remembers conversation context

## 🛠️ Tech Stack

- **Language:** Python 3.10+
- **LLM:** GPT-OSS 120B (via Groq API — free tier)
- **UI:** Streamlit *(coming soon)*
- **Voice:** Whisper + Piper TTS *(coming soon)*
- **Agents:** LangGraph *(coming soon)*

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or higher
- A free Groq API key from [console.groq.com](https://console.groq.com)

### Installation

1. Clone the repository:
```bash
   git clone https://github.com/nimeslug/NIMESLUGAI.git
   cd NIMESLUGAI
```

2. Create and activate a virtual environment:
```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Mac/Linux
   source venv/bin/activate
```

3. Install dependencies:
```bash
   pip install -r requirements.txt
```

4. Set up your API key:
   - Create a `.env` file in the project root
   - Add your Groq API key:
   GROQ_API_KEY=your_key_here
   5. Run:
```bash
   python main.py
```

## 📁 Project Structure
nimeslug/

├── main.py              # Entry point

├── config.py            # Configuration & system prompt

├── requirements.txt     # Python dependencies

├── .env                 # API keys (not committed)

├── .gitignore

└── README.md
## 🗺️ Roadmap

- [x] Basic LLM integration with bilingual support
- [ ] Streamlit chat interface
- [ ] Conversation memory
- [ ] Real-time market data (stocks, crypto, forex)
- [ ] Voice interaction (Whisper + TTS)
- [ ] Multi-agent architecture (LangGraph)
- [ ] Personal budget tracking
- [ ] Spaced-repetition economics tutor
- [ ] Daily market briefing

## ⚠️ Disclaimer

Nimeslug provides educational information only. It does **not** offer personalized investment advice. Always consult a licensed financial advisor before making financial decisions.

## 📜 License

MIT