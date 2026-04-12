"""
Backend API server for the AirPro HVAC dashboard.

Run this file when you want the frontend to connect to the backend without
starting the local terminal microphone agent.
"""

import uvicorn

from api import app as fastapi_app


def main() -> None:
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000, log_level="warning")


if __name__ == "__main__":
    main()
