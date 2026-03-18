"""Pytest fixtures for auction-backend tests."""
import os

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

# Use SQLite for fast tests
os.environ.setdefault("DB_ENGINE", "sqlite")


@pytest.fixture
def api_client():
    """Unauthenticated API client."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create a test user."""
    from users.models import User
    return User.objects.create_user(
        email="seller@example.com",
        password="TestPass123!",
        first_name="Seller",
        last_name="User",
    )


@pytest.fixture
def other_user(db):
    """Create another test user (bidder)."""
    from users.models import User
    return User.objects.create_user(
        email="bidder@example.com",
        password="TestPass123!",
        first_name="Bidder",
        last_name="User",
    )


@pytest.fixture
def auth_client(api_client, user):
    """API client authenticated as user."""
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def auth_client_other(api_client, other_user):
    """API client authenticated as other_user."""
    refresh = RefreshToken.for_user(other_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def category(db):
    """Create a test category."""
    from auctions.models import Category
    return Category.objects.create(
        name="Electronics",
        slug="electronics",
        description="Electronic items",
    )


@pytest.fixture
def auction(db, user, category):
    """Create a draft auction."""
    from auctions.models import Auction
    return Auction.objects.create(
        seller=user,
        title="Test Item",
        description="A test auction item",
        category=category,
        starting_price=100,
        current_price=100,
        status=Auction.Status.DRAFT,
    )


@pytest.fixture
def active_auction(db, user, category):
    """Create an active auction."""
    from auctions.models import Auction
    from django.utils import timezone
    return Auction.objects.create(
        seller=user,
        title="Active Item",
        description="An active auction",
        category=category,
        starting_price=100,
        current_price=100,
        status=Auction.Status.ACTIVE,
        start_time=timezone.now(),
    )


@pytest.fixture
def bid(db, active_auction, other_user):
    """Create a bid on active auction."""
    from bids.models import Bid
    from decimal import Decimal
    return Bid.objects.create(
        auction=active_auction,
        bidder=other_user,
        amount=Decimal("150.00"),
    )
