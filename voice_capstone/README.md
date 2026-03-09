# AgriAssist (Farm Consult)

AgriAssist is a simple farm consultation project.
You ask a farming question (text or voice), and the system returns guidance in plain language.

This project uses:

- FastAPI backend
- Static frontend in `static/index.html`
- SQLite for session data
- STT + LLM + TTS services through Nexus API

## What this project does

- Accepts farm questions from the UI
- Supports text and voice input
- Generates helpful farm responses
- Can return audio output for the response

## System Architecture

```text
Browser UI (static/index.html)
        |
        | HTTP API calls
        v
FastAPI Server (main.py)
   |        |        |
   |        |        +--> TTS (speech output)
   |        +-----------> LLM (answer generation)
   +--------------------> STT (speech-to-text)
        |
        v
SQLite Database (session/history)
```

## Project Structure (important parts)

```text
voice_capstone/
├── main.py
├── database.py
├── intake.py
├── memory.py
├── models.py
├── stt.py
├── tts.py
├── static/
│   └── index.html
└── README.md
```

## Run the project

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Add `.env` in `voice_capstone/`:

```env
NEXUS_API_KEY=your_key
NEXUS_BASE_URL=your_base_url
```

3. Start backend:

```bash
python main.py
```

4. Open UI:

- Preferred: `http://127.0.0.1:8000/static/index.html`
- Or open `static/index.html` directly (keep backend running)

## Notes

- This is a guidance tool, not a replacement for a licensed agronomist.
- Backend is unchanged; UI is static-only.
