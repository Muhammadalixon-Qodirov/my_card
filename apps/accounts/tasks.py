from random import randint

from celery import shared_task
from django.core.cache import cache

from apps.core.eskiz import send_sms


OTP_TTL = 60 * 5


@shared_task
def send_sms_otp(phone: str, otp_type: str = "register"):
    otp_code = str(randint(100000, 999999))
    cache.set(f'phone_otp:{phone}', otp_code, timeout=OTP_TTL)
    
    if otp_type == "forgot_password":
        message = f"Kodni hech kimga bermang. MyCard ilovasida parolni tiklash uchun bir martalik tasdiqlash kodi: {otp_code}\nBu kod 5 daqiqa davomida amal qiladi!"
    elif otp_type == "delete_account":
        message = f"Kodni hech kimga bermang. MyCard ilovasida hisobni o'chirish uchun bir martalik tasdiqlash kodi: {otp_code}\nBu kod 5 daqiqa davomida amal qiladi!"
    else:
        message = f"Kodni hech kimga bermang. MyCard ilovasida ro'yhatdan o'tish uchun bir martalik tasdiqlash kodi: {otp_code}\nBu kod 5 daqiqa davomida amal qiladi!"
    
    try:
        send_sms(phone, message)
    except Exception as exc:
        raise exc
    return True
