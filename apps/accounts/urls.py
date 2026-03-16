from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    SignInView, MyProfileView,
    RegisterView, OTPVerifyView,
    OTPLoginView, LogoutView,
    PasswordChangeView
)


urlpatterns = [
    path('login/', SignInView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', MyProfileView.as_view(), name='user-profile'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('password/change/', PasswordChangeView.as_view(), name='password-change'),

    path('register/', RegisterView.as_view(), name='register'),
    path('otp/verify/', OTPVerifyView.as_view(), name='otp-verify'),

    path('otp/login/', OTPLoginView.as_view(), name='otp-login'),
]
