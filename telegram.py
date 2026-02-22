import os

import requests

_API_BASE = "https://api.telegram.org/bot{token}/sendMessage"


def send_message(text: str):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    resp = requests.post(
        _API_BASE.format(token=token),
        json={"chat_id": chat_id, "text": text},
    )
    resp.raise_for_status()
    return resp.json()
