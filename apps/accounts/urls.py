from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import SignUpView, SignInView, MyProfileView


urlpatterns = [
    path('register/', SignUpView.as_view(), name='register'),
    path('login/', SignInView.as_view(), name='login'),
    path('profile/', MyProfileView.as_view(), name='user-profile'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
