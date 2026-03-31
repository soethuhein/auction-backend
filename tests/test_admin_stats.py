"""Admin stats API (staff-only)."""

import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestAdminStatsAPI:
    def test_admin_stats_requires_staff(self, auth_client):
        url = reverse("admin-stats")
        response = auth_client.get(url)
        assert response.status_code == 403

    def test_admin_stats_staff_ok(self, staff_auth_client, user, other_user):
        url = reverse("admin-stats")
        response = staff_auth_client.get(url)
        assert response.status_code == 200
        data = response.data
        assert data["total_users"] >= 2
        assert "active_auctions" in data
        assert "completed_auctions" in data
        assert "bids_today" in data
        assert "total_revenue" in data
        assert "commission" in data
        assert data["pending_reports"] == 0
        assert data["pending_item_approvals"] == 0

    def test_admin_stats_anonymous(self, api_client):
        url = reverse("admin-stats")
        response = api_client.get(url)
        assert response.status_code == 403
