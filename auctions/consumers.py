"""
WebSocket consumer for live auction bidding.
Broadcasts bid updates to all connected clients.
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer


class AuctionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        auction_id = self.scope["url_route"]["kwargs"]["auction_id"]
        # Normalize to ensure group name matches broadcast sender.
        self.auction_id = str(auction_id).lower()
        self.room_group_name = f"auction_{self.auction_id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

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
