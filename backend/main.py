"""Backend entrypoint for local runs and container startup.

This keeps the runtime shape close to the reference repos, where a small
entry module launches the main analytics application.
"""

from __future__ import annotations

import os

try:
    from .soccer_analytics import app
except ModuleNotFoundError as exc:
    # Only fall back when package-relative import is unavailable.
    # If a dependency inside soccer_analytics is missing (e.g. cv2), re-raise.
    if exc.name not in {"backend.soccer_analytics", "soccer_analytics"}:
        raise
    from soccer_analytics import app


def main() -> None:
    """Launch the FastAPI analytics service."""

    import uvicorn

    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", "8000"))
    uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
