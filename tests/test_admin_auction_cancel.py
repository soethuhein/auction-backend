"""Admin auction cancel API (staff-only)."""

import pytest
from django.urls import reverse

from auctions.models import Auction


@pytest.mark.django_db
class TestAdminAuctionCancelAPI:
    def test_cancel_requires_staff(self, auth_client, auction):
        url = reverse("admin-auction-cancel", kwargs={"auction_id": auction.id})
        response = auth_client.post(url)
        assert response.status_code == 403

    def test_cancel_anonymous(self, api_client, auction):
        url = reverse("admin-auction-cancel", kwargs={"auction_id": auction.id})
        response = api_client.post(url)
        assert response.status_code == 401

    def test_cancel_staff_draft_ok(self, staff_auth_client, auction):
        assert auction.status == Auction.Status.DRAFT
        url = reverse("admin-auction-cancel", kwargs={"auction_id": auction.id})
        response = staff_auth_client.post(url)
        assert response.status_code == 200
        assert response.data["status"] == "cancelled"
        auction.refresh_from_db()
        assert auction.status == Auction.Status.CANCELLED

    def test_cancel_staff_active_ok(self, staff_auth_client, active_auction):
        url = reverse("admin-auction-cancel", kwargs={"auction_id": active_auction.id})
        response = staff_auth_client.post(url)
        assert response.status_code == 200
        active_auction.refresh_from_db()
        assert active_auction.status == Auction.Status.CANCELLED

    def test_cancel_already_ended(self, staff_auth_client, auction):
        auction.status = Auction.Status.ENDED
        auction.save(update_fields=["status"])
        url = reverse("admin-auction-cancel", kwargs={"auction_id": auction.id})
        response = staff_auth_client.post(url)
        assert response.status_code == 400

    def test_cancel_twice(self, staff_auth_client, auction):
        url = reverse("admin-auction-cancel", kwargs={"auction_id": auction.id})
        assert staff_auth_client.post(url).status_code == 200
        response = staff_auth_client.post(url)
        assert response.status_code == 400
