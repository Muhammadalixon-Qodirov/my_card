from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_yasg.utils import swagger_auto_schema

from apps.accounts.models import CustomUser
from .tokens import get_tokens_for_user

from .serializers import (
    SignUpSerializer, SignInSerializer,
    UserProfileSerializer
)


class SignUpView(APIView):
    permission_classes = (AllowAny, )

    @swagger_auto_schema(request_body=SignUpSerializer)
    def post(self, request, *args, **kwargs):
        serializer = SignUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        tokens = get_tokens_for_user(user)
        return Response({"message": "User created successfully.", "tokens": tokens}, status=201)


class SignInView(APIView):
    permission_classes = (AllowAny, )
    
    @swagger_auto_schema(request_body=SignInSerializer)
    def post(self, request, *args, **kwargs):
        serializer = SignInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data['phone']
        password = serializer.validated_data['password']

        user = CustomUser.objects.filter(phone=phone).first()
        if user and user.check_password(password):
            tokens = get_tokens_for_user(user)
            return Response({"message": "Sign in successful.", "tokens": tokens}, status=200)
        else:
            return Response({"error": "Invalid phone or password."}, status=400)


class MyProfileView(APIView):
    serializer = UserProfileSerializer
    permission_classes = (IsAuthenticated, )

    @swagger_auto_schema(responses={200: UserProfileSerializer})
    def get(self, request, *args, **kwargs):
        user = request.user
        serializer = self.serializer(user)
        return Response(serializer.data, status=200)

    @swagger_auto_schema(request_body=UserProfileSerializer, responses={200: UserProfileSerializer})
    def put(self, request, *args, **kwargs):
        user = request.user
        serializer = self.serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=200)
