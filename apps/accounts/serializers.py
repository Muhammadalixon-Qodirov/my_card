from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.core.validators import validate_phone_number
from .models import CustomUser, UserDevice



def _validate_phone(value):
    try:
        validate_phone_number(value)
    except DjangoValidationError as e:
        raise serializers.ValidationError(e.messages)
    return value


class SignInSerializer(serializers.Serializer):
    phone = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        if not data.get('phone') or not data.get('password'):
            raise serializers.ValidationError("Telefon raqam va parol talab qilinadi.")
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('phone', 'first_name', 'last_name', 'gender', 'birth_date', 'is_active', 'is_staff', 'date_joined', 'last_login', 'profile_image')
        read_only_fields = ('phone', 'is_active', 'is_staff', 'date_joined', 'last_login')


class RegisterSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    first_name = serializers.CharField(max_length=50)
    last_name = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    gender = serializers.ChoiceField(choices=['male', 'female'], required=False, allow_null=True, default=None)
    birth_date = serializers.DateField(required=False, allow_null=True, default=None)
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, required=True, min_length=8)

    def validate_phone(self, value):
        value = _validate_phone(value)
        if CustomUser.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Bu raqam allaqachon ro'yxatdan o'tgan.")
        return value
    
    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Parol va parol tasdiqlash mos kelmadi.")
        return data


class OTPVerifySerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    code = serializers.CharField(max_length=6, min_length=6)

    def validate_phone(self, value):
        return _validate_phone(value)

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Kod faqat raqamlardan iborat bo'lishi kerak.")
        return value


class OTPLoginSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    code = serializers.CharField(max_length=6, min_length=6)

    def validate_phone(self, value):
        value = _validate_phone(value)
        if not CustomUser.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Bu raqam ro'yxatdan o'tmagan.")
        return value

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Kod faqat raqamlardan iborat bo'lishi kerak.")
        return value


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True, required=True, min_length=8)

    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError("Yangi parol va parol tasdiqlash mos kelmadi.")
        return data


class DeleteAccountRequestSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, required=True)


class DeleteAccountConfirmSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    code = serializers.CharField(max_length=6, min_length=6)

    def validate_phone(self, value):
        return _validate_phone(value)

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Kod faqat raqamlardan iborat bo'lishi kerak.")
        return value


class UserDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDevice
        fields = ("id", "fcm_token", "device_type", "is_active", "created_at")
        read_only_fields = ("id", "is_active", "created_at")

    def validate_fcm_token(self, value):
        if not value.strip():
            raise serializers.ValidationError("FCM token bo'sh bo'lmasligi kerak.")
        return value.strip()
