# Felicia AI

> AI Indonesia yang jujur, transparan, bisa diaudit.

Chatbot AI berbahasa Indonesia. Dibuat di Pangkalan Bun, Kalimantan Tengah.

## Fitur

- Chat real-time dengan streaming
- Dua mode otak: FAST (20b) & DEEP (120b)
- Web search (DuckDuckGo) untuk info terkini
- Jujur: kalau gak tau, bilang gak tau

## Teknologi

- **UI**: Chainlit
- **Otak**: Groq (openai/gpt-oss-120b)
- **Web Search**: DuckDuckGo (ddgs)

## Cara Jalanin

```bash
pip install -r requirements.txt
chainlit run chainlit_app.py
