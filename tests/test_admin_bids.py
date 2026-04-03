"""Admin bids list API (staff-only)."""

import pytest
from decimal import Decimal
from django.urls import reverse


@pytest.mark.django_db
class TestAdminBidsAPI:
    def test_list_requires_staff(self, auth_client):
        url = reverse("admin-bids")
        response = auth_client.get(url)
        assert response.status_code == 403

    def test_list_anonymous(self, api_client):
        url = reverse("admin-bids")
        response = api_client.get(url)
        assert response.status_code == 401

    def test_list_staff_ok(self, staff_auth_client, active_auction, other_user):
        from bids.models import Bid

        b1 = Bid.objects.create(
            auction=active_auction,
            bidder=other_user,
            amount=Decimal("175.00"),
        )
        b2 = Bid.objects.create(
            auction=active_auction,
            bidder=other_user,
            amount=Decimal("200.00"),
        )

        url = reverse("admin-bids")
        response = staff_auth_client.get(url)
        assert response.status_code == 200
        assert response.data["count"] >= 2
        ids = [r["id"] for r in response.data["results"]]
        assert str(b2.id) in ids
        assert str(b1.id) in ids
        # Newest first
        assert response.data["results"][0]["id"] == str(b2.id)
        first = response.data["results"][0]
        assert first["auction"]["id"] == str(active_auction.id)
        assert "item_title" in first["auction"]
        assert first["bidder"]["username"] == other_user.username
