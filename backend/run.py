import os

import uvicorn

from app.main import app


def main():
    host = os.getenv("ASHWEN_HOST", "127.0.0.1")
    port = int(os.getenv("ASHWEN_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
