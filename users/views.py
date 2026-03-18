from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import User
from .serializers import UserRegisterSerializer, UserSerializer
from auctions.models import Auction, Watchlist
from auctions.serializers import AuctionListSerializer, WatchlistSerializer
from bids.models import Bid
from bids.serializers import BidListSerializer


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"message": "User created successfully", "user_id": str(user.id)},
            status=status.HTTP_201_CREATED,
        )


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserDetailView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = "id"
    lookup_field = "id"


class MyAuctionsView(generics.ListAPIView):
    serializer_class = AuctionListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Auction.objects.filter(seller=self.request.user).select_related(
            "seller", "item", "item__category"
        ).order_by("-created_at")


class MyBidsView(generics.ListAPIView):
    serializer_class = BidListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Bid.objects.filter(bidder=self.request.user).select_related(
            "auction", "bidder"
        ).order_by("-created_at")


class MyWatchlistView(generics.ListAPIView):
    serializer_class = WatchlistSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Watchlist.objects.filter(user=self.request.user).select_related(
            "auction", "auction__seller", "auction__item", "auction__item__category"
        ).order_by("-created_at")
