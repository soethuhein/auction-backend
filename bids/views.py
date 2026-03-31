from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from auctions.models import Auction
from .models import Bid
from .serializers import BidCreateSerializer, BidListSerializer
from .services import place_bid


class BidCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, auction_id):
        try:
            auction = Auction.objects.get(pk=auction_id)
        except Auction.DoesNotExist:
            return Response(
                {"detail": "Auction not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if auction.seller_id == request.user.id:
            return Response(
                {"detail": "The seller cannot bid on their own auction."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = BidCreateSerializer(
            data=request.data,
            context={"auction": auction, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        bid = place_bid(
            auction=auction,
            bidder=request.user,
            amount=serializer.validated_data["amount"],
        )
        return Response(
            BidListSerializer(bid).data,
            status=status.HTTP_201_CREATED,
        )


class BidListView(generics.ListAPIView):
    serializer_class = BidListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Bid.objects.filter(bidder=self.request.user).select_related(
            "auction", "bidder"
        ).order_by("-created_at")
