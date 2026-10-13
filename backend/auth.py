
import os
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

router = APIRouter(
    prefix="/auth/discord",
    tags=["Discord"]
)

CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")

REDIRECT_URI = (
    "https://cards-minecraft.onrender.com"
    "/auth/discord/callback"
)


@router.get("/login")
def discord_login(request: Request):
    if not CLIENT_ID or not CLIENT_SECRET:
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
        "state": state
    }

    url = (
        "https://discord.com/oauth2/authorize?"
        + urlencode(parametros)
    )

    return RedirectResponse(url=url)


@router.get("/callback")
async def discord_callback(
    request: Request,
    code: str = None,
    state: str = None
):
    state_salvo = request.session.pop(
        "discord_oauth_state", None
    )

    if (
        not code
        or not state
        or not state_salvo
        or not secrets.compare_digest(state, state_salvo)
    ):
        raise HTTPException(
            status_code=400,
            detail="Autorização inválida"
        )

    async with httpx.AsyncClient(timeout=15) as client:
        resposta = await client.post(
            "https://discord.com/api/oauth2/token",
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI
            }
        )

        if resposta.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail="Não foi possível autenticar com Discord"
            )

        token = resposta.json()["access_token"]

        usuario = await client.get(
            "https://discord.com/api/users/@me",
            headers={
                "Authorization": f"Bearer {token}"
            }
        )

        if usuario.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail="Não foi possível identificar o usuário"
            )

        dados = usuario.json()

    # Guardamos somente os dados necessários
    request.session["discord_id"] = dados["id"]
    request.session["discord_nome"] = dados["username"]

    return RedirectResponse(
        url="/auth/discord/me",
        status_code=303
    )


@router.get("/me")
def discord_me(request: Request):
    discord_id = request.session.get("discord_id")
    nome = request.session.get("discord_nome")

    if not discord_id:
        raise HTTPException(
            status_code=401,
            detail="Usuário não autenticado"
        )

    return {
        "autenticado": True,
        "nome": nome,
        "discord_id": discord_id
    }
