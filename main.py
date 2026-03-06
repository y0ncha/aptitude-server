"""Compatibility module for legacy uvicorn entrypoints."""

from app.main import app, run_dev_server

__all__ = ["app", "run_dev_server"]


if __name__ == "__main__":
    run_dev_server()
