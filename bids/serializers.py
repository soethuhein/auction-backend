from rest_framework import serializers

from auctions.models import Auction

from .models import Bid
from users.serializers import UserPublicSerializer


class AuctionBidSummarySerializer(serializers.ModelSerializer):
    item_title = serializers.CharField(source="item.title", read_only=True, allow_null=True)

    class Meta:
        model = Auction
        fields = ("id", "status", "current_price", "end_time", "item_title")


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


class MyBidSerializer(serializers.ModelSerializer):
    auction = AuctionBidSummarySerializer(read_only=True)
    is_winning = serializers.SerializerMethodField()
    is_won = serializers.SerializerMethodField()

    class Meta:
        model = Bid
        fields = ("id", "amount", "created_at", "auction", "is_winning", "is_won")

    def _best_bid(self, obj):
        bids = obj.auction.bids.all()
        try:
            return bids[0]
        except IndexError:
            return None

    def get_is_winning(self, obj):
        best = self._best_bid(obj)
        return bool(best and best.id == obj.id)

    def get_is_won(self, obj):
        return (
            obj.auction.status == Auction.Status.ENDED and self.get_is_winning(obj)
        )
