from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Accept both lowercase and uppercase UUID hex characters.
    re_path(r"ws/auctions/(?P<auction_id>[0-9a-fA-F-]+)/$", consumers.AuctionConsumer.as_asgi()),
]
