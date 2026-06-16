# Repository Guidelines

## Project Structure & Module Organization

This repository is a Python FastAPI backend for the StayMatch Arabic housing assistant. The application source lives in `app/`, with `app/main.py` as the entry point and `app/api/routes.py` defining HTTP routes. Core business logic belongs in `app/services/`; NLP parsing and token logic belong in `app/nlp/` and `app/extractors/`; database connections, SQL, migrations, and repositories live under `app/database/`. Use `app/models/` for request and response models, `app/formatters/` for response shaping, `app/rag/` for retrieval features, and `app/utils/` for shared helpers. Tests live in `tests/`. Root JSON files such as `GPDataBaseMain_net.json`, `cities.json`, and `governorates.json` are static data inputs.

## Build, Test, and Development Commands

- `python -m venv venv`: create a local virtual environment.
- `source venv/bin/activate`: activate the environment on Linux/macOS.
- `pip install -r requirements.txt`: install runtime dependencies.
- `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`: run the development API server.
- `python -m unittest discover -s tests -v`: run the primary test suite.
- `python -m compileall app tests`: check Python files compile.
- `pytest --cov=app tests/`: run optional coverage checks when `pytest-cov` is installed.

## Coding Style & Naming Conventions

Use Python 3.10+ conventions with 4-space indentation. Name modules, functions, and variables in `snake_case`; name classes in `PascalCase`. Keep orchestration and workflow code in `app/services`, parsing code in `app/nlp` or `app/extractors`, and frontend-facing payload formatting in `app/formatters`. There is no repository-level formatter or linter configuration, so keep edits consistent with nearby code.

## Testing Guidelines

The project primarily uses `unittest`. Add tests as `tests/test_*.py` and name test methods `test_*`. Prefer focused regression cases for Arabic NLP behavior, price parsing, filter reset flows, search execution, and `/chat` response behavior. When changing parser behavior, include both direct extraction tests and contextual follow-up cases where relevant.

## Commit & Pull Request Guidelines

Recent history uses short version-style messages such as `v15-2` and `v14 - postfinal`; for new work, prefer clearer imperative messages like `fix price parser regression` or `add shared housing tests`. Pull requests should include a concise summary, linked issue or context, test commands run, and JSON examples or screenshots when changing `/chat` API responses.

## Security & Configuration Tips

Keep `.env` local and out of commits. Required settings include `GROQ_API_KEY`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD`. Prefer `DATABASE_URL` for chatbot PostgreSQL storage; legacy `CHATBOT_DB_*` variables are only for backward compatibility.
