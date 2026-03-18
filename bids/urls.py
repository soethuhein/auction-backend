from django.urls import path

from . import views

urlpatterns = [
    path("auctions/<uuid:auction_id>/bid/", views.BidCreateView.as_view(), name="bid-create"),
    path("bids/", views.BidListView.as_view(), name="bid-list"),
]
