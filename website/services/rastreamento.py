import os

import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL")
API_TOKEN = os.getenv("API_TOKEN")


def consultar_minuta(minuta: str):
    url = f"{API_URL}/consultar_minuta"

    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "minuta": minuta.strip(),
    }

    resposta = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=10,
    )

    resposta.raise_for_status()
    return resposta.json()