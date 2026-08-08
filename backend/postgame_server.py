"""Continuously running post-game API and single-job GPU worker."""

import uvicorn

from postgame.api import create_app

app = create_app()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
