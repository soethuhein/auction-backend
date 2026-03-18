import uuid
from django.db import models
from django.conf import settings


class Bid(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    auction = models.ForeignKey(
        "auctions.Auction",
        on_delete=models.CASCADE,
        related_name="bids",
    )
    bidder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bids",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bids"
        ordering = ["-amount", "-created_at"]
        indexes = [
            models.Index(fields=["auction"]),
        ]

    def __str__(self):
        return f"{self.bidder} - {self.amount} on {self.auction}"
