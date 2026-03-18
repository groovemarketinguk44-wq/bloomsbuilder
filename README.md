# BloomsBuilder

An AI-powered educational resource generation engine aligned with **Bloom's Taxonomy**.

Generate lesson plans, worksheets, schemes of work, and slide outlines — all locally, with no SaaS, no accounts, and no internet required (after install).

---

## Features

- **4 resource types**: Lesson Plan, Worksheet, Scheme of Work, Slide Outline
- **Bloom's Taxonomy alignment**: Every resource maps activities and questions to cognitive levels (Remember → Create)
- **AI generation**: Uses Anthropic Claude when an API key is present; falls back to high-quality demo content without one
- **Export**: PDF (WeasyPrint), DOCX (python-docx), PPTX (python-pptx, slides only)
- **Resource library**: Browse, filter, view, and delete previously generated resources
- **Local SQLite database**: No external database required

---

## Tech Stack

| Layer    | Technology              |
|----------|-------------------------|
| Backend  | FastAPI + Uvicorn       |
| Database | SQLAlchemy + SQLite     |
| Frontend | Jinja2 + HTMX + Tailwind CSS |
| AI       | Anthropic Claude API    |
| Export   | WeasyPrint / python-docx / python-pptx |

---

## Quick Start

### 1. Clone / download the project

```bash
cd blooms_builder_tool
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **WeasyPrint system dependencies** (required for PDF export only):
>
> - **macOS**: `brew install cairo pango libffi gdk-pixbuf`
> - **Ubuntu/Debian**: `sudo apt-get install libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info`
> - **Windows**: See [WeasyPrint installation docs](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows)
>
> PDF export will show an error if these are missing; all other features still work.

### 4. Configure environment (optional)

```bash
cp .env.example .env
```

Edit `.env` and add your Anthropic API key:

```env
AI_API_KEY=sk-ant-...your-key-here...
```

Without an API key the app runs in **demo mode**, generating realistic sample content. All other features (library, export, UI) are fully functional.

Get an Anthropic API key at: https://console.anthropic.com/

### 5. Run the application

```bash
uvicorn app.main:app --reload
```

### 6. Open in your browser

```
http://localhost:8000
```

---

## Environment Variables

| Variable      | Required | Default                       | Description                           |
|---------------|----------|-------------------------------|---------------------------------------|
| `AI_API_KEY`  | No       | *(none – uses demo content)*  | Anthropic API key for Claude          |
| `AI_MODEL`    | No       | `claude-haiku-4-5-20251001`   | Claude model to use for generation    |

---

## Project Structure

```
blooms_builder_tool/
├── app/
│   ├── main.py                 # FastAPI app entry point
│   ├── database.py             # SQLAlchemy engine + session
│   ├── models.py               # SQLAlchemy Resource model
│   ├── schemas.py              # Pydantic request/response schemas
│   ├── routers/
│   │   └── resources.py        # All route handlers
│   ├── services/
│   │   ├── ai_generator.py     # AI generation + mock fallback
│   │   └── export_service.py   # PDF / DOCX / PPTX export
│   ├── templates/
│   │   ├── base.html           # Base layout (nav, footer, loading)
│   │   ├── index.html          # Homepage + generation form
│   │   ├── preview.html        # Resource preview (all 4 types)
│   │   └── library.html        # Resource library
│   └── static/                 # Static assets
├── requirements.txt
├── .env.example
└── README.md
```

---

## Usage

1. **Generate** – On the homepage, select a resource type, fill in subject / key stage / topic / Bloom focus, and click **Generate Resource**.
2. **Preview** – The generated resource opens immediately with formatted layout and Bloom level badges.
3. **Export** – Download as PDF, DOCX (for lesson plans, worksheets, schemes), or PPTX (slide outlines).
4. **Library** – All generated resources are saved locally. Filter by type, view, or delete from `/library`.

---

## Extending with a different AI provider

The `ai_generator.py` service is designed to be swapped. To use a different provider:

1. Replace the `_call_ai_api()` function with your provider's API call.
2. Update the `AI_API_KEY` environment variable.
3. The prompt builders and mock fallback layer remain unchanged.

---

## License

MIT – use freely for personal and educational purposes.
