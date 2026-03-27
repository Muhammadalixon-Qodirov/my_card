from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Sum
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
    coin_balance = serializers.SerializerMethodField(read_only=True)
    total_score = serializers.SerializerMethodField(read_only=True)
    learning_progress = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CustomUser
        fields = ('phone', 'first_name', 'last_name', 'gender', 'birth_date', 'is_active', 'is_staff', 'date_joined', 'last_login', 'profile_image', 'coin_balance', 'total_score', 'learning_progress')
        read_only_fields = ('phone', 'is_active', 'is_staff', 'date_joined', 'last_login', 'coin_balance', 'total_score', 'learning_progress')

    def get_coin_balance(self, obj):
        from apps.wallet.models import CoinTransaction
        return CoinTransaction.get_balance(obj)

    def get_total_score(self, obj):
        result = obj.scores.aggregate(total=Sum('score'))['total']
        return result or 0

    def get_learning_progress(self, obj):
        from apps.education.models import Module, Test, TestAnswer

        special_tests = Test.objects.filter(is_special=True, is_active=True)
        total_special = special_tests.count()

        if total_special == 0:
            return 0.0

        # Count distinct special tests the user has answered correctly at least once
        correct_special = TestAnswer.objects.filter(
            user=obj,
            test__is_special=True,
            test__is_active=True,
            is_correct=True,
        ).values('test').distinct().count()

        special_progress = (correct_special / total_special) * 100
        remaining_pct = 100 - special_progress

        if remaining_pct == 0:
            return 100.0

        # The remaining percentage is distributed across all modules
        total_modules = Module.objects.count()
        if total_modules == 0:
            return round(special_progress, 2)

        completed_modules = obj.module_logs.filter(is_completed=True).values('module').distinct().count()
        module_contribution = (completed_modules / total_modules) * remaining_pct

        return round(special_progress + module_contribution, 2)


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
