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
    path("admin/stats/", views.AdminStatsView.as_view(), name="admin-stats"),
    path("admin/items/", views.AdminItemListView.as_view(), name="admin-items"),
    path(
        "admin/auctions/<uuid:auction_id>/cancel/",
        views.AdminAuctionCancelView.as_view(),
        name="admin-auction-cancel",
    ),
    path("admin/bids/", views.AdminBidListView.as_view(), name="admin-bids"),
    path("admin/users/", views.AdminUserListView.as_view(), name="admin-users"),
    path("admin/users/<uuid:id>/", views.AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("users/<uuid:id>/", views.UserDetailView.as_view(), name="user-detail"),
]
