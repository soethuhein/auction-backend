from decimal import Decimal

from django.conf import settings
from django.db.models import DecimalField, OuterRef, Prefetch, Subquery, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .serializers import (
    AdminUserSerializer,
    AdminUserUpdateSerializer,
    UserRegisterSerializer,
    UserSerializer,
)
from auctions.models import Auction, Item, Watchlist
from auctions.serializers import AdminItemListSerializer, AuctionListSerializer, WatchlistSerializer
from bids.models import Bid
from bids.serializers import MyBidSerializer


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
    serializer_class = MyBidSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        won_param = self.request.query_params.get("won", "").lower()
        won_only = won_param in ("1", "true", "yes")

        ordered_bids = Bid.objects.order_by("-amount", "-created_at")
        qs = (
            Bid.objects.filter(bidder=self.request.user)
            .select_related("auction", "auction__item")
            .prefetch_related(Prefetch("auction__bids", queryset=ordered_bids))
            .order_by("-created_at")
        )

        if won_only:
            winning_bid_pk = Subquery(
                Bid.objects.filter(auction_id=OuterRef("auction_id"))
                .order_by("-amount", "-created_at")
                .values("id")[:1]
            )
            qs = qs.filter(
                auction__status=Auction.Status.ENDED,
                id=winning_bid_pk,
            )

        return qs


class MyWatchlistView(generics.ListAPIView):
    serializer_class = WatchlistSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Watchlist.objects.filter(user=self.request.user).select_related(
            "auction", "auction__seller", "auction__item", "auction__item__category"
        ).order_by("-created_at")


class AdminItemListView(generics.ListAPIView):
    """Paginated list of all items (all owners) for staff dashboard."""

    permission_classes = [IsAdminUser]
    serializer_class = AdminItemListSerializer

    def get_queryset(self):
        return (
            Item.objects.all()
            .select_related("category", "owner")
            .prefetch_related("images")
            .order_by("-created_at")
        )


class AdminUserListView(generics.ListAPIView):
    """Paginated user list for staff dashboard."""

    permission_classes = [IsAdminUser]
    serializer_class = AdminUserSerializer
    queryset = User.objects.all().order_by("-date_joined")


class AdminUserDetailView(generics.RetrieveUpdateAPIView):
    """View user; PATCH `is_active` only to ban or unban."""

    permission_classes = [IsAdminUser]
    queryset = User.objects.all()
    lookup_url_kwarg = "id"
    lookup_field = "id"

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return AdminUserUpdateSerializer
        return AdminUserSerializer

    def perform_update(self, serializer):
        user = serializer.instance
        if user.pk == self.request.user.pk and serializer.validated_data.get("is_active") is False:
            raise PermissionDenied("You cannot deactivate your own account.")
        if (user.is_staff or user.is_superuser) and serializer.validated_data.get("is_active") is False:
            raise PermissionDenied("Cannot deactivate staff or superuser accounts via this endpoint.")
        serializer.save()


class AdminStatsView(APIView):
    """Aggregate metrics for staff dashboard (platform-wide)."""

    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        today = timezone.now().date()
        sale_field = DecimalField(max_digits=12, decimal_places=2)

        total_users = User.objects.count()
        active_auctions = Auction.objects.filter(status=Auction.Status.ACTIVE).count()
        completed_auctions = Auction.objects.filter(status=Auction.Status.ENDED).count()
        bids_today = Bid.objects.filter(created_at__date=today).count()

        winning_amount = (
            Bid.objects.filter(auction_id=OuterRef("pk"))
            .order_by("-amount", "-created_at")
            .values("amount")[:1]
        )
        ended = Auction.objects.filter(status=Auction.Status.ENDED).annotate(
            winning_amount=Subquery(winning_amount, output_field=sale_field),
        ).annotate(
            sale=Coalesce("winning_amount", "current_price", output_field=sale_field),
        )
        agg = ended.aggregate(total=Sum("sale"))
        total_revenue = agg["total"] or Decimal("0")

        rate = Decimal(str(getattr(settings, "COMMISSION_RATE", 0.05)))
        commission = (total_revenue * rate).quantize(Decimal("0.01"))

        return Response(
            {
                "total_users": total_users,
                "active_auctions": active_auctions,
                "completed_auctions": completed_auctions,
                "bids_today": bids_today,
                "total_revenue": str(total_revenue),
                "commission": str(commission),
                "commission_rate": float(rate),
                "pending_reports": 0,
                "pending_item_approvals": 0,
            }
        )
