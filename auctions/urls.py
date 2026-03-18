from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import AuctionViewSet, CategoryViewSet

router = DefaultRouter()
router.register(r"auctions", AuctionViewSet, basename="auction")
router.register(r"categories", CategoryViewSet, basename="category")

urlpatterns = [
    path("", include(router.urls)),
]
