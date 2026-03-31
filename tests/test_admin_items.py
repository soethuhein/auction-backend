"""Admin items list API (staff-only)."""

import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestAdminItemsAPI:
    def test_list_requires_staff(self, auth_client):
        url = reverse("admin-items")
        response = auth_client.get(url)
        assert response.status_code == 403

    def test_list_staff_ok(self, staff_auth_client, user, other_user, category):
        from auctions.models import Item

        Item.objects.create(
            owner=user,
            item_type="digital",
            title="User item",
            category=category,
            attributes={},
        )
        Item.objects.create(
            owner=other_user,
            item_type="digital",
            title="Other item",
            category=category,
            attributes={},
        )

        url = reverse("admin-items")
        response = staff_auth_client.get(url)
        assert response.status_code == 200
        assert response.data["count"] >= 2
        titles = {r["title"] for r in response.data["results"]}
        assert "User item" in titles
        assert "Other item" in titles
        sample = next(r for r in response.data["results"] if r["title"] == "Other item")
        assert "owner" in sample
        assert sample["owner"]["email"] == other_user.email

    def test_list_anonymous(self, api_client):
        url = reverse("admin-items")
        response = api_client.get(url)
        assert response.status_code == 401
