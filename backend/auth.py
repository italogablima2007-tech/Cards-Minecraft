
import os
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/auth/discord", tags=["Discord"])

CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")

REDIRECT_URI = (
    "https://cards-minecraft.onrender.com"
    "/auth/discord/callback"
)


@router.get("/login")
def discord_login(request: Request):
    if not CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="Discord não configurado"
        )

    state = secrets.token_urlsafe(32)

    request.session["discord_oauth_state"] = state

    parametros = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "identify",
        "state": state,
        "prompt": "consent"
    }

    url = (
        "https://discord.com/oauth2/authorize?"
        + urlencode(parametros)
    )

    return RedirectResponse(url=url)
