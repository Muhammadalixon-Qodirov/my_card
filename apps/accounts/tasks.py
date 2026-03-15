from random import randint

from celery import shared_task
from django.core.cache import cache

from apps.core.eskiz import send_sms


OTP_TTL = 60 * 5


@shared_task
def send_sms_otp(phone: str):
    otp_code = str(randint(100000, 999999))
    cache.set(f'phone_otp:{phone}', otp_code, timeout=OTP_TTL)
    message = "Bu Eskiz dan test"
    # message = f"MyCard ilovasida bir martalik tasdiqlash kodi: <code>{otp_code}</code>\nBu kod 5 daqiqa davomida amal qiladi!\nKodni hech kimga bermang!"
    try:
        send_sms(phone, message)
    except Exception as exc:
        raise exc
    return True
