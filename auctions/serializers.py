from rest_framework import serializers
from datetime import timedelta
from django.utils import timezone
from .models import Auction, Category, Watchlist
from users.serializers import UserPublicSerializer
from bids.serializers import BidListSerializer


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "description")


class AuctionListSerializer(serializers.ModelSerializer):
    seller = UserPublicSerializer(read_only=True)
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Auction
        fields = (
            "id",
            "title",
            "starting_price",
            "current_price",
            "status",
            "start_time",
            "end_time",
            "image_urls",
            "seller",
            "category",
            "created_at",
        )


class AuctionDetailSerializer(serializers.ModelSerializer):
    seller = UserPublicSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    bids = serializers.SerializerMethodField()

    class Meta:
        model = Auction
        fields = (
            "id",
            "title",
            "description",
            "starting_price",
            "current_price",
            "reserve_price",
            "status",
            "start_time",
            "end_time",
            "duration_days",
            "duration_hours",
            "duration_minutes",
            "image_urls",
            "seller",
            "category",
            "bids",
            "created_at",
            "updated_at",
        )

    def get_bids(self, obj):
        bids = obj.bids.all()[:10]
        return BidListSerializer(bids, many=True).data


class AuctionCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Auction
        fields = (
            "id",
            "title",
            "description",
            "category",
            "starting_price",
            "reserve_price",
            "image_urls",
            "start_time",
            "end_time",
            "duration_days",
            "duration_hours",
            "duration_minutes",
        )
        read_only_fields = ("id",)

    def validate_starting_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Starting price must be positive.")
        return value

    def validate(self, data):
        instance = getattr(self, "instance", None)
        now = timezone.now()

        start_time = data.get("start_time", instance.start_time if instance else None)
        if not start_time:
            raise serializers.ValidationError({"start_time": "This field is required."})
        if timezone.is_naive(start_time):
            start_time = timezone.make_aware(start_time)
        if start_time < now:
            raise serializers.ValidationError(
                {"start_time": "start_time must be greater than or equal to current time."}
            )

        duration_days = data.get("duration_days", instance.duration_days if instance else 0) or 0
        duration_hours = data.get("duration_hours", instance.duration_hours if instance else 0) or 0
        duration_minutes = data.get("duration_minutes", instance.duration_minutes if instance else 0) or 0
        end_time = data.get("end_time", instance.end_time if instance else None)

        if not end_time and not (duration_days or duration_hours or duration_minutes):
            raise serializers.ValidationError(
                {"non_field_errors": ["Provide end_time or at least one duration value."]}
            )

        # Normalize to duration fields so model-computed end_time stays consistent.
        if end_time and not (duration_days or duration_hours or duration_minutes):
            if timezone.is_naive(end_time):
                end_time = timezone.make_aware(end_time)
            if end_time <= start_time:
                raise serializers.ValidationError(
                    {"end_time": "end_time must be greater than start_time."}
                )
            total_minutes = int((end_time - start_time).total_seconds() // 60)
            days, rem = divmod(total_minutes, 24 * 60)
            hours, minutes = divmod(rem, 60)
            duration_days = days
            duration_hours = hours
            duration_minutes = minutes

        data["start_time"] = start_time
        data["duration_days"] = duration_days
        data["duration_hours"] = duration_hours
        data["duration_minutes"] = duration_minutes
        data["status"] = (
            Auction.Status.ACTIVE if start_time <= now else Auction.Status.SCHEDULED
        )
        return data


class WatchlistSerializer(serializers.ModelSerializer):
    auction = AuctionListSerializer(read_only=True)

    class Meta:
        model = Watchlist
        fields = ("id", "auction", "created_at")
        read_only_fields = ("id",)
