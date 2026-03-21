from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.exceptions import ValidationError, PermissionDenied

from .models import Auction, Category, Watchlist, Item, ItemImage
from .serializers import (
    AuctionListSerializer,
    AuctionDetailSerializer,
    AuctionCreateUpdateSerializer,
    CategorySerializer,
    WatchlistSerializer,
    ItemSerializer,
    ItemImageSerializer,
)
from .permissions import IsSellerOrReadOnly
from .tasks import schedule_auction_tasks


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = "id"


class ItemViewSet(viewsets.ModelViewSet):
    serializer_class = ItemSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        return Item.objects.filter(owner=self.request.user).select_related("category", "owner").prefetch_related("images")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(
        detail=True,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser],
        permission_classes=[IsAuthenticated],
    )
    def upload_image(self, request, id=None):
        item = self.get_object()
        image_file = request.FILES.get("image")
        if not image_file:
            return Response({"detail": "image file is required"}, status=status.HTTP_400_BAD_REQUEST)
        alt_text = request.data.get("alt_text", "")
        sort_order = int(request.data.get("sort_order") or 0)
        img = ItemImage.objects.create(item=item, image=image_file, alt_text=alt_text, sort_order=sort_order)
        return Response(ItemImageSerializer(img, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    def images(self, request, id=None):
        item = self.get_object()
        qs = item.images.all()
        return Response(ItemImageSerializer(qs, many=True, context={"request": request}).data)

    @action(detail=True, methods=["delete"], url_path=r"images/(?P<image_id>[^/.]+)", permission_classes=[IsAuthenticated])
    def delete_image(self, request, id=None, image_id=None):
        item = self.get_object()
        try:
            img = item.images.get(pk=image_id)
        except ItemImage.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        img.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AuctionViewSet(viewsets.ModelViewSet):
    queryset = Auction.objects.select_related("seller", "item", "item__category").prefetch_related("bids")
    permission_classes = [IsAuthenticatedOrReadOnly, IsSellerOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["item__title", "item__description"]
    ordering_fields = ["created_at", "end_time", "current_price"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        category = self.request.query_params.get("category")
        if not category:
            return qs
        if category.isdigit():
            return qs.filter(item__category_id=int(category))
        return qs.filter(item__category__slug=category)

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return AuctionCreateUpdateSerializer
        if self.action == "list":
            return AuctionListSerializer
        return AuctionDetailSerializer

    def perform_create(self, serializer):
        item_id = serializer.validated_data.get("item_id")
        if not item_id:
            raise ValidationError({"item_id": "This field is required."})
        try:
            item = Item.objects.get(pk=item_id)
        except Item.DoesNotExist:
            raise ValidationError({"item_id": "Invalid item_id"})
        if item.owner_id != self.request.user.id:
            raise PermissionDenied("You can only auction your own items.")
        auction = serializer.save(seller=self.request.user, item=item)
        schedule_auction_tasks(auction)

    def perform_update(self, serializer):
        # Item ownership is enforced by IsSellerOrReadOnly (seller == owner at creation time).
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
