from django.core.cache import cache
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import CustomUser
from apps.accounts.tasks import send_sms_otp, OTP_TTL
from .tokens import get_tokens_for_user
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import UserDevice
from .serializers import (
    SignInSerializer, UserProfileSerializer,
    RegisterSerializer, OTPVerifySerializer,
    OTPLoginSerializer, LogoutSerializer,
    PasswordChangeSerializer,
    DeleteAccountRequestSerializer,
    DeleteAccountConfirmSerializer,
    UserDeviceSerializer,
    ForgotPasswordRequestSerializer,
    ForgotPasswordResetSerializer,
)


REGISTER_PENDING_KEY = 'register_pending:{phone}'
OTP_KEY = 'phone_otp:{phone}'
DELETE_ACCOUNT_PENDING_KEY = 'delete_account_pending:{phone}'
FORGOT_PASSWORD_PENDING_KEY = 'forgot_password_pending:{phone}'



class SignInView(APIView):
    permission_classes = (AllowAny,)

    @swagger_auto_schema(request_body=SignInSerializer, tags=["Auth"])
    def post(self, request, *args, **kwargs):
        serializer = SignInSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data['phone']
        password = serializer.validated_data['password']

        user = CustomUser.objects.filter(phone=phone).first()
        if user and user.check_password(password):
            return Response({"message": "Muvaffaqiyatli kirildi.", "tokens": get_tokens_for_user(user)}, status=200)
        return Response({"error": "Telefon raqam yoki parol noto'g'ri."}, status=400)



class MyProfileView(APIView):
    permission_classes = (IsAuthenticated, )

    @swagger_auto_schema(responses={200: UserProfileSerializer})
    def get(self, request, *args, **kwargs):
        serializer = UserProfileSerializer(request.user, context={"request": request})
        return Response(serializer.data, status=200)

    @swagger_auto_schema(request_body=UserProfileSerializer, responses={200: UserProfileSerializer})
    def put(self, request, *args, **kwargs):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=200)



class RegisterView(APIView):
    permission_classes = (AllowAny,)

    @swagger_auto_schema(request_body=RegisterSerializer, tags=["Auth"])
    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data['phone']
        otp_key = OTP_KEY.format(phone=phone)

        if cache.get(otp_key):
            ttl = cache.ttl(otp_key) or 0
            return Response(
                {"message": "OTP allaqachon yuborilgan.", "wait_seconds": ttl},
                status=429,
            )

        pending_key = REGISTER_PENDING_KEY.format(phone=phone)
        cache.set(pending_key, {
            'phone': phone,
            'first_name': serializer.validated_data['first_name'],
            'last_name': serializer.validated_data.get('last_name', ''),
            'gender': serializer.validated_data.get('gender'),
            'password': serializer.validated_data['password'],
            'birth_date': str(serializer.validated_data['birth_date'])
                          if serializer.validated_data.get('birth_date') else None,
        }, timeout=OTP_TTL)

        send_sms_otp.apply_async(args=[phone, "register"], countdown=1)
        return Response({"status": True, "message": "OTP kod yuborildi. 5 daqiqa ichida tasdiqlang."}, status=200)



class OTPVerifyView(APIView):
    permission_classes = (AllowAny,)

    @swagger_auto_schema(request_body=OTPVerifySerializer, tags=["Auth"])
    def post(self, request, *args, **kwargs):
        serializer = OTPVerifySerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data['phone']
        code = serializer.validated_data['code']

        otp_key = OTP_KEY.format(phone=phone)
        cached_code = cache.get(otp_key)
        if not cached_code or cached_code != code:
            return Response({"message": "Kod noto'g'ri yoki muddati o'tgan."}, status=400)

        pending_key = REGISTER_PENDING_KEY.format(phone=phone)
        user_data = cache.get(pending_key)
        if not user_data:
            return Response({"message": "Ro'yxatdan o'tish ma'lumotlari topilmadi. Qaytadan urinib ko'ring."}, status=400)

        cache.delete(otp_key)
        cache.delete(pending_key)

        user = CustomUser.objects.create_user(
            phone=user_data['phone'],
            first_name=user_data['first_name'],
            last_name=user_data.get('last_name', ''),
            gender=user_data.get('gender'),
            birth_date=user_data.get('birth_date')
        )
        user.set_password(user_data['password'])
        user.save()

        return Response({
            "status": True,
            "message": "Ro'yxatdan o'tish muvaffaqiyatli.",
            "tokens": get_tokens_for_user(user),
        }, status=201)



class OTPLoginView(APIView):
    permission_classes = (AllowAny,)

    @swagger_auto_schema(request_body=OTPLoginSerializer, tags=["Auth"])
    def post(self, request, *args, **kwargs):
        serializer = OTPLoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data['phone']
        code = serializer.validated_data['code']

        cached_code = cache.get(f'phone_otp:{phone}')
        if not cached_code or cached_code != code:
            return Response({"message": "Kod noto'g'ri yoki muddati o'tgan."}, status=400)

        cache.delete(f'phone_otp:{phone}')

        user = CustomUser.objects.get(phone=phone)
        return Response({
            "status": True,
            "message": "Muvaffaqiyatli kirildi.",
            "tokens": get_tokens_for_user(user),
        }, status=200)


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(request_body=LogoutSerializer, tags=["Auth"])
    def post(self, request, *args, **kwargs):
        serializer = LogoutSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data['refresh'])
            token.blacklist()
        except TokenError:
            return Response({"message": "Token yaroqsiz yoki allaqachon bekor qilingan."}, status=400)
        return Response({"status": True, "message": "Muvaffaqiyatli chiqildi."}, status=205)


class PasswordChangeView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = PasswordChangeSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']

        if not user.check_password(old_password):
            return Response({"message": "Eski parol noto'g'ri."}, status=400)

        user.set_password(new_password)
        user.save()
        return Response({"status": True, "message": "Parol muvaffaqiyatli o'zgartirildi."}, status=200)


class ForgotPasswordRequestView(APIView):
    permission_classes = (AllowAny,)

    @swagger_auto_schema(request_body=ForgotPasswordRequestSerializer, tags=["Auth"])
    def post(self, request, *args, **kwargs):
        serializer = ForgotPasswordRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data['phone']
        otp_key = OTP_KEY.format(phone=phone)

        if cache.get(otp_key):
            ttl = cache.ttl(otp_key) or 0
            return Response(
                {"message": "OTP allaqachon yuborilgan.", "wait_seconds": ttl},
                status=429,
            )

        pending_key = FORGOT_PASSWORD_PENDING_KEY.format(phone=phone)
        cache.set(pending_key, True, timeout=OTP_TTL)
        send_sms_otp.apply_async(args=[phone, "forgot_password"], countdown=1)

        return Response(
            {"status": True, "message": "Tasdiqlash kodi yuborildi. 5 daqiqa ichida tasdiqlang."},
            status=200,
        )


class ForgotPasswordResetView(APIView):
    permission_classes = (AllowAny,)

    @swagger_auto_schema(request_body=ForgotPasswordResetSerializer, tags=["Auth"])
    def post(self, request, *args, **kwargs):
        serializer = ForgotPasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data['phone']
        code = serializer.validated_data['code']
        new_password = serializer.validated_data['new_password']

        pending_key = FORGOT_PASSWORD_PENDING_KEY.format(phone=phone)
        if not cache.get(pending_key):
            return Response(
                {"message": "Avval parolni tiklash so'rovini yuboring."},
                status=400,
            )

        otp_key = OTP_KEY.format(phone=phone)
        cached_code = cache.get(otp_key)
        if not cached_code or cached_code != code:
            return Response({"message": "Kod noto'g'ri yoki muddati o'tgan."}, status=400)

        try:
            user = CustomUser.objects.get(phone=phone, is_active=True)
        except CustomUser.DoesNotExist:
            return Response({"message": "Foydalanuvchi topilmadi."}, status=404)

        cache.delete(otp_key)
        cache.delete(pending_key)

        user.set_password(new_password)
        user.save()

        return Response(
            {"status": True, "message": "Parol muvaffaqiyatli yangilandi."},
            status=200,
        )


class DeleteAccountRequestView(APIView):
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(request_body=DeleteAccountRequestSerializer)
    def post(self, request, *args, **kwargs):
        serializer = DeleteAccountRequestSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        password = serializer.validated_data['password']
        if not user.check_password(password):
            return Response({"message": "Parol noto'g'ri."}, status=400)

        phone = user.phone
        otp_key = OTP_KEY.format(phone=phone)

        if cache.get(otp_key):
            ttl = cache.ttl(otp_key) or 0
            return Response(
                {"message": "OTP allaqachon yuborilgan.", "wait_seconds": ttl},
                status=429,
            )

        delete_pending_key = DELETE_ACCOUNT_PENDING_KEY.format(phone=phone)
        cache.set(delete_pending_key, True, timeout=OTP_TTL)
        send_sms_otp.apply_async(args=[phone, "delete_account"], countdown=1)

        return Response(
            {"status": True, "message": "Tasdiqlash kodi yuborildi. 5 daqiqa ichida tasdiqlang."},
            status=200,
        )


class DeleteAccountConfirmView(APIView):
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(request_body=DeleteAccountConfirmSerializer)
    def post(self, request, *args, **kwargs):
        serializer = DeleteAccountConfirmSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        phone = serializer.validated_data['phone']
        code = serializer.validated_data['code']

        if phone != user.phone:
            return Response({"message": "Telefon raqam login foydalanuvchiga mos emas."}, status=400)

        delete_pending_key = DELETE_ACCOUNT_PENDING_KEY.format(phone=phone)
        if not cache.get(delete_pending_key):
            return Response({"message": "Avval account o'chirish uchun so'rov yuboring."}, status=400)

        otp_key = OTP_KEY.format(phone=phone)
        cached_code = cache.get(otp_key)
        if not cached_code or cached_code != code:
            return Response({"message": "Kod noto'g'ri yoki muddati o'tgan."}, status=400)

        cache.delete(otp_key)
        cache.delete(delete_pending_key)

        user.delete()

        return Response({"status": True, "message": "Hisob muvaffaqiyatli o'chirildi."}, status=200)


class UserDeviceView(APIView):
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(request_body=UserDeviceSerializer, tags=["Devices"])
    def post(self, request):
        token = request.data.get("fcm_token", "").strip()
        device_type = request.data.get("device_type", "android")

        if not token:
            return Response({"detail": "fcm_token majburiy."}, status=400)

        UserDevice.objects.filter(fcm_token=token).exclude(user=request.user).update(is_active=False)

        device, created = UserDevice.objects.update_or_create(
            fcm_token=token,
            defaults={"user": request.user, "device_type": device_type, "is_active": True},
        )
        serializer = UserDeviceSerializer(device)
        status_code = 201 if created else 200
        return Response(serializer.data, status=status_code)

    @swagger_auto_schema(tags=["Devices"])
    def delete(self, request):
        token = request.data.get("fcm_token", "").strip()
        if not token:
            return Response({"detail": "fcm_token majburiy."}, status=400)
        updated = UserDevice.objects.filter(user=request.user, fcm_token=token).update(is_active=False)
        if not updated:
            return Response({"detail": "Qurilma topilmadi."}, status=404)
        return Response({"detail": "Qurilma o'chirildi."}, status=200)
