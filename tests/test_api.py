"""API endpoint tests for auction-backend."""
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta


class TestCategoriesAPI:
    """Tests for categories endpoints."""

    def test_list_categories(self, api_client, category):
        url = reverse("category-list")
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["count"] >= 1
        slugs = [c["slug"] for c in response.data["results"]]
        assert "electronics" in slugs

    def test_retrieve_category(self, api_client, category):
        url = reverse("category-detail", kwargs={"id": category.id})
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["name"] == "Electronics"


class TestAuctionsAPI:
    """Tests for auctions endpoints."""

    def test_list_auctions(self, api_client, auction):
        url = reverse("auction-list")
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["count"] >= 1

    def test_create_auction(self, auth_client):
        url = reverse("auction-list")
        start_time = (timezone.now() + timedelta(hours=2)).isoformat()
        data = {
            "title": "New Auction",
            "description": "Description",
            "starting_price": "99.99",
            "start_time": start_time,
            "duration_hours": 2,
            "image_urls": [],
        }
        response = auth_client.post(url, data, format="json")
        assert response.status_code == 201
        assert response.data["title"] == "New Auction"
        assert "id" in response.data
        from auctions.models import Auction
        created = Auction.objects.get(pk=response.data["id"])
        assert created.status == "scheduled"

    def test_create_auction_requires_auth(self, api_client):
        url = reverse("auction-list")
        data = {
            "title": "New Auction",
            "description": "Desc",
            "starting_price": "10",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == 401

    def test_retrieve_auction(self, api_client, auction):
        url = reverse("auction-detail", kwargs={"pk": auction.id})
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["title"] == "Test Item"

    def test_update_auction_seller(self, auth_client, auction):
        url = reverse("auction-detail", kwargs={"pk": auction.id})
        data = {
            "title": "Updated Title",
            "start_time": (timezone.now() + timedelta(hours=1)).isoformat(),
            "duration_minutes": 30,
        }
        response = auth_client.patch(url, data, format="json")
        assert response.status_code == 200
        auction.refresh_from_db()
        assert auction.title == "Updated Title"
        assert auction.status == "scheduled"

    def test_update_auction_non_seller_forbidden(self, auth_client_other, auction):
        url = reverse("auction-detail", kwargs={"pk": auction.id})
        response = auth_client_other.patch(url, {"title": "Hacked"}, format="json")
        assert response.status_code == 403

    def test_start_auction(self, auth_client, auction):
        url = reverse("auction-start", kwargs={"pk": auction.id})
        response = auth_client.post(
            url,
            {"duration_days": 1, "duration_hours": 0, "duration_minutes": 0},
            format="json",
        )
        assert response.status_code == 200
        auction.refresh_from_db()
        assert auction.status == "active"
        assert auction.start_time is not None
        assert auction.end_time is not None

    def test_start_auction_forbidden_non_seller(self, auth_client_other, auction):
        url = reverse("auction-start", kwargs={"pk": auction.id})
        response = auth_client_other.post(url)
        assert response.status_code == 403

    def test_create_auction_requires_start_time(self, auth_client):
        url = reverse("auction-list")
        data = {
            "title": "Missing Start",
            "description": "Description",
            "starting_price": "99.99",
            "duration_hours": 1,
        }
        response = auth_client.post(url, data, format="json")
        assert response.status_code == 400
        assert "start_time" in response.data

    def test_create_auction_requires_end_or_duration(self, auth_client):
        url = reverse("auction-list")
        data = {
            "title": "Missing Duration",
            "description": "Description",
            "starting_price": "99.99",
            "start_time": (timezone.now() + timedelta(hours=1)).isoformat(),
        }
        response = auth_client.post(url, data, format="json")
        assert response.status_code == 400

    def test_create_auction_rejects_past_start_time(self, auth_client):
        url = reverse("auction-list")
        data = {
            "title": "Past Start",
            "description": "Description",
            "starting_price": "99.99",
            "start_time": (timezone.now() - timedelta(minutes=5)).isoformat(),
            "duration_hours": 1,
        }
        response = auth_client.post(url, data, format="json")
        assert response.status_code == 400
        assert "start_time" in response.data


class TestBidsAPI:
    """Tests for bids endpoints."""

    def test_place_bid(self, auth_client_other, active_auction):
        url = reverse("bid-create", kwargs={"auction_id": active_auction.id})
        response = auth_client_other.post(
            url, {"amount": "200.00"}, format="json"
        )
        assert response.status_code == 201
        assert response.data["amount"] == "200.00"

    def test_place_bid_below_current_rejected(self, auth_client_other, active_auction):
        url = reverse("bid-create", kwargs={"auction_id": active_auction.id})
        response = auth_client_other.post(
            url, {"amount": "50.00"}, format="json"
        )
        assert response.status_code == 400

    def test_place_bid_on_draft_rejected(self, auth_client_other, auction):
        url = reverse("bid-create", kwargs={"auction_id": auction.id})
        response = auth_client_other.post(
            url, {"amount": "150.00"}, format="json"
        )
        assert response.status_code == 400

    def test_place_bid_requires_auth(self, api_client, active_auction):
        url = reverse("bid-create", kwargs={"auction_id": active_auction.id})
        response = api_client.post(url, {"amount": "150.00"}, format="json")
        assert response.status_code == 401

    def test_list_my_bids(self, auth_client_other, bid):
        url = reverse("bid-list")
        response = auth_client_other.get(url)
        assert response.status_code == 200
        assert response.data["count"] >= 1


class TestWatchlistAPI:
    """Tests for watchlist endpoints."""

    def test_add_to_watchlist(self, auth_client_other, auction):
        url = reverse("auction-add-to-watchlist", kwargs={"pk": auction.id})
        response = auth_client_other.post(url)
        assert response.status_code in (200, 201)

    def test_remove_from_watchlist(self, auth_client, user, auction):
        from auctions.models import Watchlist
        Watchlist.objects.create(user=user, auction=auction)
        url = reverse("auction-remove-from-watchlist", kwargs={"pk": auction.id})
        response = auth_client.post(url)
        assert response.status_code == 200

    def test_my_watchlist(self, auth_client, user, auction):
        from auctions.models import Watchlist
        Watchlist.objects.create(user=user, auction=auction)
        url = reverse("my-watchlist")
        response = auth_client.get(url)
        assert response.status_code == 200
        assert response.data["count"] >= 1


class TestUserProfileAPI:
    """Tests for user profile endpoints."""

    def test_my_auctions(self, auth_client, auction):
        url = reverse("my-auctions")
        response = auth_client.get(url)
        assert response.status_code == 200
        assert response.data["count"] >= 1

    def test_my_bids(self, auth_client_other, bid):
        url = reverse("my-bids")
        response = auth_client_other.get(url)
        assert response.status_code == 200
        assert response.data["count"] >= 1
