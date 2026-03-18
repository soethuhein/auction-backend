from rest_framework import serializers
from .models import Bid
from users.serializers import UserPublicSerializer


class BidCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bid
        fields = ("amount",)

    def validate_amount(self, value):
        auction = self.context["auction"]
        if auction.status != "active":
            raise serializers.ValidationError(
                "Bids can only be placed on active auctions."
            )
        min_amount = auction.current_price
        if value <= min_amount:
            raise serializers.ValidationError(
                f"Bid must be higher than current price (${min_amount})."
            )
        return value


class BidListSerializer(serializers.ModelSerializer):
    bidder = UserPublicSerializer(read_only=True)

    class Meta:
        model = Bid
        fields = ("id", "bidder", "amount", "created_at")
