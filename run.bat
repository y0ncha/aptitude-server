@echo off
setlocal

set "UVICORN_RELOAD=true"
set "UV_CACHE_DIR=.uv-cache"

echo Starting FastAPI dev server
echo   API:  http://127.0.0.1:8000
echo   Docs: http://127.0.0.1:8000/docs
echo   Stop: Ctrl+C
echo.

uv run python -m app.main
