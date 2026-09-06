"""Development command for the FastAPI delivery adapter."""

from __future__ import annotations

import uvicorn

from library_management.api.config import ApiSettings


def main() -> None:
    settings = ApiSettings.from_environment()
    uvicorn.run(
        "library_management.api.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment.value == "local",
    )


if __name__ == "__main__":
    main()
