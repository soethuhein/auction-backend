"""Model tests for auction-backend."""
import pytest
from decimal import Decimal


from auctions.models import Auction, Category, Watchlist
from bids.models import Bid
from users.models import User


class TestUserModel:
    """Tests for User model."""

    def test_create_user(self, db):
        user = User.objects.create_user(
            email="test@example.com",
            password="TestPass123!",
        )
        assert user.email == "test@example.com"
        assert user.username == "test@example.com"
        assert user.check_password("TestPass123!")

    def test_create_user_with_extra_fields(self, db):
        user = User.objects.create_user(
            email="extra@example.com",
            password="TestPass123!",
            first_name="Test",
            last_name="User",
        )
        assert user.first_name == "Test"
        assert user.last_name == "User"

    def test_email_unique(self, db, user):
        with pytest.raises(Exception):
            User.objects.create_user(
                email=user.email,
                password="TestPass123!",
            )

    def test_str(self, user):
        assert str(user) == user.email


class TestCategoryModel:
    """Tests for Category model."""

    def test_create_category(self, db):
        cat = Category.objects.create(
            name="Art",
            slug="art",
            description="Art items",
        )
        assert cat.name == "Art"
        assert cat.slug == "art"

    def test_str(self, category):
        assert str(category) == "Electronics"


class TestAuctionModel:
    """Tests for Auction model."""

    def test_create_auction(self, db, user, category):
        auction = Auction.objects.create(
            seller=user,
            title="Painting",
            description="A painting",
            category=category,
            starting_price=Decimal("50.00"),
        )
        assert auction.status == Auction.Status.DRAFT
        assert auction.current_price == Decimal("50.00")

    def test_current_price_defaults_to_starting_price(self, auction):
        assert auction.current_price == auction.starting_price

    def test_status_choices(self):
        assert Auction.Status.DRAFT == "draft"
        assert Auction.Status.ACTIVE == "active"
        assert Auction.Status.ENDED == "ended"

    def test_str(self, auction):
        assert str(auction) == "Test Item"


class TestBidModel:
    """Tests for Bid model."""

    def test_create_bid(self, db, active_auction, other_user):
        bid = Bid.objects.create(
            auction=active_auction,
            bidder=other_user,
            amount=Decimal("200.00"),
        )
        assert bid.amount == Decimal("200.00")
        assert bid.bidder == other_user

    def test_str(self, bid):
        assert "150" in str(bid)
        assert str(bid.bidder) in str(bid)


class TestWatchlistModel:
    """Tests for Watchlist model."""

    def test_create_watchlist(self, db, user, auction):
        watch = Watchlist.objects.create(user=user, auction=auction)
        assert watch.user == user
        assert watch.auction == auction

    def test_unique_user_auction(self, db, user, auction):
        Watchlist.objects.create(user=user, auction=auction)
        with pytest.raises(Exception):
            Watchlist.objects.create(user=user, auction=auction)
