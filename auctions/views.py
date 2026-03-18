from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.response import Response

from .models import Auction, Category, Watchlist
from .serializers import (
    AuctionListSerializer,
    AuctionDetailSerializer,
    AuctionCreateUpdateSerializer,
    CategorySerializer,
    WatchlistSerializer,
)
from .permissions import IsSellerOrReadOnly
from .tasks import schedule_auction_tasks


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = "id"


class AuctionViewSet(viewsets.ModelViewSet):
    queryset = Auction.objects.select_related("seller", "category").prefetch_related("bids")
    permission_classes = [IsAuthenticatedOrReadOnly, IsSellerOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "end_time", "current_price"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return AuctionCreateUpdateSerializer
        if self.action == "list":
            return AuctionListSerializer
        return AuctionDetailSerializer

    def perform_create(self, serializer):
        auction = serializer.save(seller=self.request.user)
        schedule_auction_tasks(auction)

    def perform_update(self, serializer):
        auction = serializer.save()
        schedule_auction_tasks(auction)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def start(self, request, pk=None):
        from django.utils import timezone

        auction = self.get_object()
        if auction.seller_id != request.user.id:
            return Response(
                {"detail": "Only the seller can start this auction."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if auction.status != Auction.Status.DRAFT:
            return Response(
                {"detail": "Only draft auctions can be started."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = request.data or {}
        start_time = data.get("start_time")
        duration_days = data.get("duration_days", auction.duration_days)
        duration_hours = data.get("duration_hours", auction.duration_hours)
        duration_minutes = data.get("duration_minutes", auction.duration_minutes)

        if start_time:
            from django.utils.dateparse import parse_datetime
            parsed = parse_datetime(start_time) if isinstance(start_time, str) else start_time
            if parsed is None:
                return Response(
                    {"detail": "Invalid start_time format. Use ISO 8601 (e.g. 2026-03-10T20:00:00Z)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            start_time = parsed
            if timezone.is_naive(start_time):
                start_time = timezone.make_aware(start_time)
        else:
            start_time = timezone.now()

        if not (duration_days or duration_hours or duration_minutes):
            return Response(
                {"detail": "Duration required. Set duration_days, duration_hours, and/or duration_minutes."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        auction.start_time = start_time
        auction.duration_days = duration_days or 0
        auction.duration_hours = duration_hours or 0
        auction.duration_minutes = duration_minutes or 0
        auction.compute_end_time()
        auction.current_price = auction.starting_price

        now = timezone.now()
        if start_time <= now:
            auction.status = Auction.Status.ACTIVE
            auction.save()
            from .broadcasts import broadcast_auction_started
            broadcast_auction_started(
                auction.id,
                start_time=auction.start_time,
                end_time=auction.end_time,
                current_price=auction.current_price,
            )
        else:
            auction.status = Auction.Status.SCHEDULED
            auction.save()

        schedule_auction_tasks(auction)
        return Response(AuctionDetailSerializer(auction).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def add_to_watchlist(self, request, pk=None):
        auction = self.get_object()
        _, created = Watchlist.objects.get_or_create(
            user=request.user,
            auction=auction,
        )
        return Response(
            {"detail": "Added to watchlist" if created else "Already in watchlist"},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def remove_from_watchlist(self, request, pk=None):
        auction = self.get_object()
        deleted, _ = Watchlist.objects.filter(
            user=request.user,
            auction=auction,
        ).delete()
        return Response(
            {"detail": "Removed from watchlist" if deleted else "Not in watchlist"},
            status=status.HTTP_200_OK,
        )
