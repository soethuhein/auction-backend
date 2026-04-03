"""Admin item detail / update / images API (staff-only)."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse


@pytest.mark.django_db
class TestAdminItemDetailAPI:
    def test_get_requires_staff(self, auth_client, item):
        url = reverse("admin-item-detail", kwargs={"id": item.id})
        assert auth_client.get(url).status_code == 403

    def test_get_anonymous(self, api_client, item):
        url = reverse("admin-item-detail", kwargs={"id": item.id})
        assert api_client.get(url).status_code == 401

    def test_get_staff_any_owner(self, staff_auth_client, item):
        url = reverse("admin-item-detail", kwargs={"id": item.id})
        response = staff_auth_client.get(url)
        assert response.status_code == 200
        assert response.data["title"] == item.title
        assert "owner" in response.data
        assert response.data["owner"]["email"]

    def test_patch_staff(self, staff_auth_client, item, category):
        url = reverse("admin-item-detail", kwargs={"id": item.id})
        response = staff_auth_client.patch(
            url,
            {"title": "Admin updated title", "category_id": category.id},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["title"] == "Admin updated title"
        item.refresh_from_db()
        assert item.title == "Admin updated title"

    def test_images_list_staff(self, staff_auth_client, item):
        url = reverse("admin-item-images", kwargs={"id": item.id})
        response = staff_auth_client.get(url)
        assert response.status_code == 200
        assert isinstance(response.data, list)

    def test_upload_image_staff(self, staff_auth_client, item):
        upload_url = reverse("admin-item-upload-image", kwargs={"id": item.id})
        f = SimpleUploadedFile(
            "a.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01", content_type="image/png"
        )
        response = staff_auth_client.post(
            upload_url,
            {"image": f, "alt_text": "x", "sort_order": 0},
            format="multipart",
        )
        assert response.status_code == 201
        assert "image_url" in response.data
