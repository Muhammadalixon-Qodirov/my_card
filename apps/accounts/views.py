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

from .serializers import (
    SignInSerializer,
    UserProfileSerializer,
    RegisterSerializer,
    OTPVerifySerializer,
    OTPLoginSerializer,
    LogoutSerializer,
)


REGISTER_PENDING_KEY = 'register_pending:{phone}'
OTP_KEY = 'phone_otp:{phone}'



class SignInView(APIView):
    permission_classes = (AllowAny,)

    @swagger_auto_schema(request_body=SignInSerializer)
    def post(self, request, *args, **kwargs):
        serializer = SignInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data['phone']
        password = serializer.validated_data['password']

        user = CustomUser.objects.filter(phone=phone).first()
        if user and user.check_password(password):
            return Response({"message": "Muvaffaqiyatli kirildi.", "tokens": get_tokens_for_user(user)}, status=200)
        return Response({"error": "Telefon raqam yoki parol noto'g'ri."}, status=400)



class MyProfileView(APIView):
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(responses={200: UserProfileSerializer})
    def get(self, request, *args, **kwargs):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=200)

    @swagger_auto_schema(request_body=UserProfileSerializer, responses={200: UserProfileSerializer})
    def put(self, request, *args, **kwargs):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=200)



class RegisterView(APIView):
    permission_classes = (AllowAny,)

    @swagger_auto_schema(request_body=RegisterSerializer, tags=["Auth"])
    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
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
            'birth_date': str(serializer.validated_data['birth_date'])
                          if serializer.validated_data.get('birth_date') else None,
        }, timeout=OTP_TTL)

        send_sms_otp.apply_async(args=[phone], countdown=1)
        return Response({"status": True, "message": "OTP kod yuborildi. 5 daqiqa ichida tasdiqlang."}, status=200)



class OTPVerifyView(APIView):
    permission_classes = (AllowAny,)

    @swagger_auto_schema(request_body=OTPVerifySerializer, tags=["Auth"])
    def post(self, request, *args, **kwargs):
        serializer = OTPVerifySerializer(data=request.data)
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
            birth_date=user_data.get('birth_date'),
        )

        return Response({
            "status": True,
            "message": "Ro'yxatdan o'tish muvaffaqiyatli.",
            "tokens": get_tokens_for_user(user),
        }, status=201)



class OTPLoginView(APIView):
    permission_classes = (AllowAny,)

    @swagger_auto_schema(request_body=OTPLoginSerializer, tags=["OTP"])
    def post(self, request, *args, **kwargs):
        serializer = OTPLoginSerializer(data=request.data)
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
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data['refresh'])
            token.blacklist()
        except TokenError:
            return Response({"message": "Token yaroqsiz yoki allaqachon bekor qilingan."}, status=400)
        return Response({"status": True, "message": "Muvaffaqiyatli chiqildi."}, status=205)
