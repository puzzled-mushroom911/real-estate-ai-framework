# Python Conventions

## Style
- snake_case for files, functions, and variables
- Standalone scripts with `if __name__ == "__main__":` guards
- Use pathlib over os.path for all file operations
- Use argparse for CLI tools
- Type hints on all function signatures
- Docstrings on public functions (Google style)

## Project Structure
- `tools/` is organized by function: rag_tools/, crm_tools/, guide_converters/, data_importers/, youtube_analyzers/, utilities/
- Each subdirectory contains standalone scripts (not a monolithic package)
- Config files stored in home directory (~/.config/re-agent/ or similar)
- Environment variables for credentials -- never hardcode API keys
- `.env` files for local development, never committed to git

## Dependencies
- Python 3.10+
- RAG tools: chromadb, sentence-transformers
- CRM tools: requests, python-dotenv
- LLM tools: transformers, torch (or API-based alternatives)
- YouTube tools: yt-dlp, ffmpeg (system dependency)
- Install per-project with requirements.txt, not globally

## Error Handling
- Use try/except with specific exception types
- Log errors with the logging module (not print statements in production)
- Fail gracefully with meaningful error messages
- Return structured results (dict or dataclass), not raw strings

## Testing
- test_*.py naming pattern
- Tests live alongside source files
- Use pytest as the test runner
- Mock external API calls in tests
