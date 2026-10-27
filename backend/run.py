import os

import uvicorn

from app.config import get_config

config = get_config()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=config.DEBUG)
