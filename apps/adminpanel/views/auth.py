from datetime import timedelta

from django.contrib.auth.models import update_last_login
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import CustomUser
from ..mixins import AdminAPIMixin
from ..serializers import AdminUserSerializer
from ..throttles import AdminLoginThrottle

ADMIN_TOKEN_LIFETIME = timedelta(days=7)


class AdminLoginView(APIView):
    """Faqat superuser uchun kirish. Mobil ilova login endpointiga ta'sir qilmaydi."""

    permission_classes = (AllowAny,)
    authentication_classes = ()
    throttle_classes = (AdminLoginThrottle,)
    swagger_schema = None

    def post(self, request):
        phone = str(request.data.get("phone") or "").strip().replace(" ", "")
        password = str(request.data.get("password") or "")
        if not phone or not password:
            return Response({"detail": "Telefon raqam va parol talab qilinadi."}, status=400)

        user = CustomUser.objects.filter(phone=phone).first()
        if not user or not user.check_password(password):
            return Response({"detail": "Telefon raqam yoki parol noto'g'ri."}, status=400)
        if not (user.is_active and user.is_superuser):
            return Response({"detail": "Sizda admin panelga kirish huquqi yo'q."}, status=403)

        token = AccessToken.for_user(user)
        token.set_exp(lifetime=ADMIN_TOKEN_LIFETIME)
        token["scope"] = "admin"
        update_last_login(None, user)

        return Response({
            "access": str(token),
            "expires_in": int(ADMIN_TOKEN_LIFETIME.total_seconds()),
            "user": AdminUserSerializer(user, context={"request": request}).data,
        })


class AdminMeView(AdminAPIMixin, APIView):
    def get(self, request):
        return Response(AdminUserSerializer(request.user, context={"request": request}).data)
