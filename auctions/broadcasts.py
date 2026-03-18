"""
WebSocket broadcast helpers for auction events.
"""
import logging
from asgiref.sync import async_to_sync

logger = logging.getLogger("auctions")


def _send_to_channel(auction_id, event_type, payload):
    """Send event to auction WebSocket channel."""
    try:
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        group_name = f"auction_{auction_id}"
        async_to_sync(channel_layer.group_send)(
            group_name,
            {"type": event_type, "auction_id": str(auction_id), **payload},
        )
    except Exception as e:
        logger.warning("WebSocket broadcast failed: %s", e)


def broadcast_auction_started(auction_id, start_time=None, end_time=None, current_price=None):
    """Broadcast auction_started to WebSocket channel."""
    payload = {"status": "active"}
    if start_time is not None:
        payload["start_time"] = start_time.isoformat() if hasattr(start_time, "isoformat") else str(start_time)
    if end_time is not None:
        payload["end_time"] = end_time.isoformat() if hasattr(end_time, "isoformat") else str(end_time)
    if current_price is not None:
        payload["current_price"] = str(current_price)
    logger.info("Broadcasting auction_started auction_id=%s", auction_id)
    _send_to_channel(auction_id, "auction_started", payload)


def broadcast_auction_ended(auction_id):
    """Broadcast auction_ended to WebSocket channel."""
    logger.info("Broadcasting auction_ended auction_id=%s", auction_id)
    _send_to_channel(auction_id, "auction_ended", {"status": "ended"})
