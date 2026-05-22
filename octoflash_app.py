"""
octoflash_app.py
---

Entrypoint helper — run this script to start the Octoflash AI backend.
"""
import uvicorn


def main() -> None:
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8008,
        reload=True,
    )


if __name__ == "__main__":
    main()
