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

    def test_create_auction_draft(self, auth_client, category):
        url = reverse("auction-list")
        item_url = reverse("item-list")
        item = auth_client.post(
            item_url,
            {
                "item_type": "digital",
                "title": "New Item",
                "description": "Description",
                "category_id": str(category.id),
                "attributes": {"platform": "Steam"},
            },
            format="json",
        ).data
        data = {"item_id": item["id"], "starting_price": "99.99"}
        response = auth_client.post(url, data, format="json")
        assert response.status_code == 201
        assert "id" in response.data
        from auctions.models import Auction
        created = Auction.objects.get(pk=response.data["id"])
        assert created.status == "draft"

    def test_create_auction_requires_auth(self, api_client):
        url = reverse("auction-list")
        data = {
            "starting_price": "10",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == 401

    def test_retrieve_auction(self, api_client, auction):
        url = reverse("auction-detail", kwargs={"pk": auction.id})
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["item"]["title"] == "Test Item"

    def test_auction_detail_ended_includes_winner(self, api_client, active_auction, other_user):
        from auctions.models import Auction
        from bids.models import Bid

        Bid.objects.create(
            auction=active_auction,
            bidder=other_user,
            amount=Decimal("200.00"),
        )
        active_auction.current_price = Decimal("200.00")
        active_auction.status = Auction.Status.ENDED
        active_auction.save()
        url = reverse("auction-detail", kwargs={"pk": active_auction.id})
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["winner"] is not None
        assert str(response.data["winner"]["id"]) == str(other_user.id)
        assert response.data["winning_price"] == "200.00"

    def test_auction_detail_ended_no_bids_winner_null(self, api_client, active_auction):
        from auctions.models import Auction

        active_auction.status = Auction.Status.ENDED
        active_auction.save()
        url = reverse("auction-detail", kwargs={"pk": active_auction.id})
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["winner"] is None
        assert response.data["winning_price"] is None

    def test_update_auction_seller(self, auth_client, auction):
        url = reverse("auction-detail", kwargs={"pk": auction.id})
        data = {
            "start_time": (timezone.now() + timedelta(hours=1)).isoformat(),
            "duration_minutes": 30,
        }
        response = auth_client.patch(url, data, format="json")
        assert response.status_code == 200
        auction.refresh_from_db()
        assert auction.status == "scheduled"

    def test_update_auction_non_seller_forbidden(self, auth_client_other, auction):
        url = reverse("auction-detail", kwargs={"pk": auction.id})
        response = auth_client_other.patch(url, {"duration_minutes": 15}, format="json")
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

    def test_create_auction_requires_item_id(self, auth_client):
        url = reverse("auction-list")
        data = {
            "starting_price": "99.99",
            "duration_hours": 1,
        }
        response = auth_client.post(url, data, format="json")
        assert response.status_code == 400
        assert "item_id" in response.data

    def test_create_auction_requires_start_time_when_scheduling(self, auth_client, category):
        url = reverse("auction-list")
        item_url = reverse("item-list")
        item = auth_client.post(
            item_url,
            {
                "item_type": "digital",
                "title": "Sched Item",
                "description": "Description",
                "category_id": str(category.id),
                "attributes": {},
            },
            format="json",
        ).data
        data = {
            "item_id": item["id"],
            "starting_price": "99.99",
            "duration_hours": 1,
        }
        response = auth_client.post(url, data, format="json")
        assert response.status_code == 400
        assert "start_time" in response.data

    def test_create_auction_requires_end_or_duration_when_scheduling(self, auth_client, category):
        url = reverse("auction-list")
        item_url = reverse("item-list")
        item = auth_client.post(
            item_url,
            {
                "item_type": "digital",
                "title": "Missing Dur",
                "description": "Description",
                "category_id": str(category.id),
                "attributes": {},
            },
            format="json",
        ).data
        data = {
            "item_id": item["id"],
            "starting_price": "99.99",
            "start_time": (timezone.now() + timedelta(minutes=5)).isoformat(),
        }
        response = auth_client.post(url, data, format="json")
        assert response.status_code == 400
        assert "non_field_errors" in response.data

    def test_create_auction_rejects_past_start_time(self, auth_client, category):
        url = reverse("auction-list")
        item_url = reverse("item-list")
        item = auth_client.post(
            item_url,
            {
                "item_type": "digital",
                "title": "Past Start",
                "description": "Description",
                "category_id": str(category.id),
                "attributes": {},
            },
            format="json",
        ).data
        data = {
            "item_id": item["id"],
            "starting_price": "99.99",
            "start_time": (timezone.now() - timedelta(minutes=5)).isoformat(),
            "duration_hours": 1,
        }
        response = auth_client.post(url, data, format="json")
        assert response.status_code == 400
        assert "start_time" in response.data


class TestItemsAPI:
    def test_create_item(self, auth_client, category):
        url = reverse("item-list")
        response = auth_client.post(
            url,
            {
                "item_type": "digital",
                "title": "Digital Key",
                "description": "Game key",
                "category_id": str(category.id),
                "attributes": {"platform": "Steam", "region": "global"},
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["title"] == "Digital Key"
        assert response.data["category"]["id"] == category.id


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

    def test_place_bid_seller_rejected(self, auth_client, active_auction):
        url = reverse("bid-create", kwargs={"auction_id": active_auction.id})
        response = auth_client.post(url, {"amount": "200.00"}, format="json")
        assert response.status_code == 400
        assert "seller" in str(response.data).lower()

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
        row = next(r for r in response.data["results"] if r["id"] == str(bid.id))
        assert row["auction"]["id"] == str(bid.auction_id)
        assert row["auction"]["item_title"] == "Test Item"
        assert row["is_winning"] is True
        assert row["is_won"] is False

    def test_my_bids_won_filter_only_winning_ended(self, auth_client_other, user, item, other_user):
        from auctions.models import Auction
        from bids.models import Bid

        ended_a = Auction.objects.create(
            seller=user,
            item=item,
            starting_price=50,
            current_price=200,
            status=Auction.Status.ENDED,
        )
        Bid.objects.create(auction=ended_a, bidder=other_user, amount=Decimal("100.00"))
        Bid.objects.create(auction=ended_a, bidder=other_user, amount=Decimal("200.00"))

        url = reverse("my-bids")
        response = auth_client_other.get(url, {"won": "true"})
        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["amount"] == "200.00"
        assert response.data["results"][0]["is_won"] is True

    def test_my_bids_won_filter_excludes_active_auctions(self, auth_client_other, bid):
        url = reverse("my-bids")
        response = auth_client_other.get(url, {"won": "true"})
        assert response.status_code == 200
        assert response.data["count"] == 0
