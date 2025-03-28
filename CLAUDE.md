# SQL-Agent Development Guidelines

## Project Status
- See [SESSION_SUMMARY.md](SESSION_SUMMARY.md) for the latest development progress
- See [NEXT_SESSION.md](NEXT_SESSION.md) for planned tasks and issues to address
- See [TEST_RESULTS.md](TEST_RESULTS.md) for detailed test results and system status
- See [CODING_ROUTINE.md](CODING_ROUTINE.md) for development practices and documentation standards

## Daily Documentation
- All session summaries follow the date-based naming format: `SESSION_SUMMARY_YYYY-MM-DD.md`
- Next session planning files follow: `NEXT_SESSION_YYYY-MM-DD.md`
- The main SESSION_SUMMARY.md and NEXT_SESSION.md files link to the latest dated versions

## Build & Run Commands
- `make install` - Set up virtual environment and pre-commit hooks
- `make check` - Run linting and type checking
- `make test` - Run all tests with pytest
- `python -m pytest tests/specific_test_file.py::test_function` - Run specific test
- `uv venv .venv` - Create virtual environment 
- `uv pip install -e .` - Install package in development mode
- `python app/main.py` - Start application (http://127.0.0.1:8046/)

## Ollama Configuration
- Local Ollama is installed in `/home/coder/bin/ollama`
- Available models: `qwen2.5-coder:0.5b` (has tensor initialization issues)
- Switch between local and remote mode using `/local` and `/remote` commands
- Ollama service can be started with `/home/coder/bin/ollama serve`

## Test Scripts
- `test_basic_ollama.py` - Tests Ollama installation and connectivity
- `test_sqlite.py` - Tests database files and connectivity
- `test_direct_sql.py` - Tests direct SQL query execution
- `test_minimal_app.py` - Tests minimal application functionality

## Code Style
- **Types**: Use strict type annotations (mypy configured with disallow_untyped_defs)
- **Naming**: snake_case for functions/variables, PascalCase for classes, ALL_CAPS for constants
- **Imports**: Standard library first, third-party next, project imports last
- **Formatting**: Pre-commit hooks enforce formatting with Ruff
- **Error Handling**: Use specific exceptions, handle early returns, and use logger
- **Documentation**: Google-style docstrings with Args/Returns sections
- **Organization**: Use dataclasses, clear separation of public/private methods
- **Logging**: Always use the configured logger from utils.logger