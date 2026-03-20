from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import CoinTransactionViewSet

router = DefaultRouter()
router.register("transactions", CoinTransactionViewSet, basename="coin-transaction")

urlpatterns = [
    path("", include(router.urls)),
]
