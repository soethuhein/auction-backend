"""
Bid placement service.
Centralized for reuse in API, Celery tasks, or other consumers.
"""
import logging
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger("bids")


def place_bid(auction, bidder, amount):
    from .models import Bid

    bid = Bid.objects.create(
        auction=auction,
        bidder=bidder,
        amount=amount,
    )
    auction.current_price = amount
    auction.save(update_fields=["current_price", "updated_at"])

    # Broadcast to WebSocket for live bidding
    _broadcast_bid(auction, bid)
    logger.info("Bid placed auction_id=%s amount=%s bidder_id=%s", auction.id, amount, bidder.id)

    return bid


def _broadcast_bid(auction, bid):
    """Send new bid to WebSocket channel for live updates."""
    try:
        channel_layer = get_channel_layer()
        group_name = f"auction_{auction.id}"
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "bid_update",
                "bid": {
                    "id": str(bid.id),
                    "amount": str(bid.amount),
                    "bidder": {
                        "id": str(bid.bidder.id),
                        "username": bid.bidder.username,
                    },
                    "created_at": bid.created_at.isoformat(),
                },
                "current_price": str(auction.current_price),
            },
        )
    except Exception:
        # Fail silently if Channels/Redis not configured
        pass
