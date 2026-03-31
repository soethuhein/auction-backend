"""Admin user list / ban API (staff-only)."""

import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestAdminUsersAPI:
    def test_list_requires_staff(self, auth_client):
        url = reverse("admin-users")
        response = auth_client.get(url)
        assert response.status_code == 403

    def test_list_staff_ok(self, staff_auth_client, user, other_user):
        url = reverse("admin-users")
        response = staff_auth_client.get(url)
        assert response.status_code == 200
        assert response.data["count"] >= 2
        assert len(response.data["results"]) >= 1

    def test_list_anonymous(self, api_client):
        url = reverse("admin-users")
        response = api_client.get(url)
        assert response.status_code == 401

    def test_ban_regular_user(self, staff_auth_client, other_user):
        assert other_user.is_active
        url = reverse("admin-user-detail", kwargs={"id": other_user.id})
        response = staff_auth_client.patch(url, {"is_active": False}, format="json")
        assert response.status_code == 200
        assert response.data["is_active"] is False
        other_user.refresh_from_db()
        assert other_user.is_active is False

    def test_cannot_ban_self(self, staff_auth_client, staff_user):
        url = reverse("admin-user-detail", kwargs={"id": staff_user.id})
        response = staff_auth_client.patch(url, {"is_active": False}, format="json")
        assert response.status_code == 403

    def test_cannot_ban_staff(self, staff_auth_client, user, staff_user):
        url = reverse("admin-user-detail", kwargs={"id": staff_user.id})
        response = staff_auth_client.patch(url, {"is_active": False}, format="json")
        assert response.status_code == 403
