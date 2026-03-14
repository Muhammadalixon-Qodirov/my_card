from rest_framework import serializers

from .models import CustomUser


class SignUpSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, required=True, min_length=8)

    class Meta:
        model = CustomUser
        fields = ('phone', 'password', 'confirm_password', 'first_name', 'last_name', 'gender', 'birth_date')

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = CustomUser.objects.create_user(**validated_data)
        return user


class SignInSerializer(serializers.Serializer):
    phone = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        phone = data.get('phone')
        password = data.get('password')

        if not phone or not password:
            raise serializers.ValidationError("Both phone and password are required.")

        return data


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('phone', 'first_name', 'last_name', 'gender', 'birth_date', 'is_active', 'is_staff', 'date_joined', 'last_login')
        read_only_fields = ('phone', 'is_active', 'is_staff', 'date_joined', 'last_login')
