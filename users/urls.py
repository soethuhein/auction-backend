from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", views.MeView.as_view(), name="me"),
    path("me/auctions/", views.MyAuctionsView.as_view(), name="my-auctions"),
    path("me/bids/", views.MyBidsView.as_view(), name="my-bids"),
    path("me/watchlist/", views.MyWatchlistView.as_view(), name="my-watchlist"),
    path("users/<uuid:id>/", views.UserDetailView.as_view(), name="user-detail"),
]
