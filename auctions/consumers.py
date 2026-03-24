"""
WebSocket consumer for live auction bidding.
Broadcasts bid updates and viewer count to all connected clients.
"""
import json
from typing import Optional

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings


def _incr_viewers(auction_id: str) -> Optional[int]:
    """Atomically increment viewer count; return new count or None if Redis unavailable."""
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL)
        key = f"auction_viewers:{auction_id}"
        return r.incr(key)
    except Exception:
        return None


def _decr_viewers(auction_id: str) -> Optional[int]:
    """Atomically decrement viewer count; return new count or None if Redis unavailable."""
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL)
        key = f"auction_viewers:{auction_id}"
        count = r.decr(key)
        if count < 0:
            r.set(key, 0)
            return 0
        return count
    except Exception:
        return None


class AuctionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        auction_id = self.scope["url_route"]["kwargs"]["auction_id"]
        # Normalize to ensure group name matches broadcast sender.
        self.auction_id = str(auction_id).lower()
        self.room_group_name = f"auction_{self.auction_id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        count = await sync_to_async(_incr_viewers)(self.auction_id)
        if count is not None:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "viewer_count_update",
                    "auction_id": self.auction_id,
                    "viewer_count": count,
                },
            )

    async def disconnect(self, close_code):
        count = await sync_to_async(_decr_viewers)(self.auction_id)
        if count is not None:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "viewer_count_update",
                    "auction_id": self.auction_id,
                    "viewer_count": count,
                },
            )
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def viewer_count_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "viewer_count_update",
            "viewer_count": event["viewer_count"],
        }))

    async def bid_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "bid_update",
            "bid": event["bid"],
            "current_price": event["current_price"],
        }))

    async def auction_started(self, event):
        await self.send(text_data=json.dumps({
            "type": "auction_started",
            "auction_id": event["auction_id"],
            "status": event.get("status", "active"),
            "start_time": event.get("start_time"),
            "end_time": event.get("end_time"),
            "current_price": event.get("current_price"),
        }))

    async def auction_ended(self, event):
        await self.send(text_data=json.dumps({
            "type": "auction_ended",
            "auction_id": event["auction_id"],
            "status": event["status"],
        }))
