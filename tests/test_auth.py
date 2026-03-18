"""Authentication tests for auction-backend."""
import pytest
from django.urls import reverse


class TestRegister:
    """Tests for user registration."""

    def test_register_success(self, api_client, db):
        url = reverse("register")
        data = {
            "email": "new@example.com",
            "password": "TestPass123!",
            "first_name": "New",
            "last_name": "User",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == 201
        assert "user_id" in response.data
        assert "message" in response.data

    def test_register_duplicate_email(self, api_client, user):
        url = reverse("register")
        data = {
            "email": user.email,
            "password": "TestPass123!",
            "first_name": "Test",
            "last_name": "User",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == 400

    def test_register_weak_password(self, api_client, db):
        url = reverse("register")
        data = {
            "email": "weak@example.com",
            "password": "123",
            "first_name": "Test",
            "last_name": "User",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == 400


class TestLogin:
    """Tests for JWT login."""

    def test_login_success(self, api_client, user):
        url = reverse("token_obtain_pair")
        data = {"email": user.email, "password": "TestPass123!"}
        response = api_client.post(url, data, format="json")
        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data

    def test_login_wrong_password(self, api_client, user):
        url = reverse("token_obtain_pair")
        data = {"email": user.email, "password": "WrongPass123!"}
        response = api_client.post(url, data, format="json")
        assert response.status_code == 401

    def test_login_invalid_user(self, api_client, db):
        url = reverse("token_obtain_pair")
        data = {"email": "nonexistent@example.com", "password": "TestPass123!"}
        response = api_client.post(url, data, format="json")
        assert response.status_code == 401


class TestTokenRefresh:
    """Tests for token refresh."""

    def test_refresh_success(self, api_client, user):
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        url = reverse("token_refresh")
        response = api_client.post(
            url, {"refresh": str(refresh)}, format="json"
        )
        assert response.status_code == 200
        assert "access" in response.data


class TestMe:
    """Tests for /auth/me/ endpoint."""

    def test_me_authenticated(self, auth_client, user):
        url = reverse("me")
        response = auth_client.get(url)
        assert response.status_code == 200
        assert response.data["email"] == user.email

    def test_me_unauthenticated(self, api_client, db):
        url = reverse("me")
        response = api_client.get(url)
        assert response.status_code == 401
