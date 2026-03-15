import requests
from django.core.cache import cache
from django.conf import settings


ESKIZ_BASE_URL = "https://notify.eskiz.uz/api"
ESKIZ_TOKEN_CACHE_KEY = "eskiz_auth_token"
ESKIZ_TOKEN_TTL = 60 * 60 * 24 * 29



def _get_token() -> str:
    token = cache.get(ESKIZ_TOKEN_CACHE_KEY)
    if token:
        return token

    response = requests.post(
        f"{ESKIZ_BASE_URL}/auth/login",
        data={
            "email": settings.ESKIZ_EMAIL,
            "password": settings.ESKIZ_PASSWORD,
        },
        timeout=10,
    )
    response.raise_for_status()
    token = response.json()["data"]["token"]
    cache.set(ESKIZ_TOKEN_CACHE_KEY, token, timeout=ESKIZ_TOKEN_TTL)
    return token


def _refresh_token() -> str:
    cache.delete(ESKIZ_TOKEN_CACHE_KEY)
    return _get_token()


def send_sms(phone: str, message: str) -> dict:
    token = _get_token()

    payload = {
        "mobile_phone": phone.replace("+", ""),
        "message": message,
        "from": settings.ESKIZ_SENDER_NAME,
    }

    def _do_request(auth_token: str):
        return requests.post(
            f"{ESKIZ_BASE_URL}/message/sms/send",
            data=payload,
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10,
        )

    resp = _do_request(token)
    if resp.status_code == 401:
        token = _refresh_token()
        resp = _do_request(token)

    resp.raise_for_status()
    return resp.json()
