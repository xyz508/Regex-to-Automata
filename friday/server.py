"""Friday's web server. Run:  python server.py   then open http://localhost:8000"""

import hmac
import os
import secrets
from pathlib import Path

HERE = Path(__file__).parent


def _load_env_file():
    """Read KEY=VALUE lines from .env so beginners don't have to set env vars by hand."""
    env = HERE / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file()

import anthropic  # noqa: E402  (imported after .env so the API key is visible)
import uvicorn  # noqa: E402
from fastapi import FastAPI, Header, HTTPException  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

import brain  # noqa: E402
import store  # noqa: E402
import tools  # noqa: E402


def _passcode() -> str:
    """Every request needs this code, so a public tunnel URL can't be used by strangers."""
    code = os.environ.get("FRIDAY_PASSCODE", "").strip()
    if code:
        return code
    path = store.DATA_DIR / "passcode.txt"
    if path.exists():
        return path.read_text().strip()
    store.DATA_DIR.mkdir(exist_ok=True)
    code = secrets.token_hex(4)
    path.write_text(code)
    return code


PASSCODE = _passcode()
app = FastAPI(title="Friday", docs_url=None, redoc_url=None)
conversation = brain.Conversation()


def _auth(key: str | None):
    if not key or not hmac.compare_digest(key.encode(), PASSCODE.encode()):
        raise HTTPException(status_code=401, detail="Wrong passcode")


class AskBody(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


@app.get("/api/check")
async def check(x_friday_key: str | None = Header(default=None)):
    _auth(x_friday_key)
    return {"ok": True, "name": brain.USER_NAME}


@app.post("/api/ask")
async def ask(body: AskBody, x_friday_key: str | None = Header(default=None)):
    _auth(x_friday_key)
    try:
        return await conversation.ask(body.text.strip())
    except anthropic.AuthenticationError:
        return {"reply": "My API key is missing or wrong. Check the .env file.", "actions": [], "error": True}
    except anthropic.RateLimitError:
        return {"reply": "I'm being rate limited. Give me a minute.", "actions": [], "error": True}
    except anthropic.APIConnectionError:
        return {"reply": "I can't reach my brain. Check the internet connection.", "actions": [], "error": True}
    except anthropic.APIStatusError as e:
        print("Claude API error:", e.status_code, e.message)
        return {"reply": f"Something went wrong on my side, error {e.status_code}.", "actions": [], "error": True}


@app.post("/api/reset")
async def reset(x_friday_key: str | None = Header(default=None)):
    _auth(x_friday_key)
    conversation.reset()
    return {"ok": True}


@app.get("/api/alerts")
async def alerts(x_friday_key: str | None = Header(default=None)):
    _auth(x_friday_key)
    return {"alerts": tools.due_alerts()}


@app.get("/")
async def index():
    return FileResponse(HERE / "static" / "index.html")


app.mount("/", StaticFiles(directory=HERE / "static"), name="static")


if __name__ == "__main__":
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        print("\n  !! No ANTHROPIC_API_KEY found. Put it in the .env file (see README).\n")
    port = int(os.environ.get("FRIDAY_PORT", "8000"))
    print(f"\n  Friday is online:  http://localhost:{port}")
    print(f"  Your passcode:     {PASSCODE}\n")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
