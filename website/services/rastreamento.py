import os

import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = (os.getenv("API_URL") or "").rstrip("/")
API_TOKEN = os.getenv("API_TOKEN") or ""


class RastreamentoConfigError(RuntimeError):
    pass


def consultar_minuta(minuta: str):
    if not API_URL or not API_TOKEN:
        raise RastreamentoConfigError("API de rastreamento não configurada.")

    url = f"{API_URL}/consultar_minuta"
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {"minuta": (minuta or "").strip()}

    resposta = requests.post(url, json=payload, headers=headers, timeout=10)
    resposta.raise_for_status()
    return resposta.json()
