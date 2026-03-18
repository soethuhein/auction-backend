import uuid
from datetime import timedelta
from django.db import models
from django.conf import settings


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "categories"
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Item(models.Model):
    class ItemType(models.TextChoices):
        DIGITAL = "digital", "Digital"
        PHYSICAL = "physical", "Physical"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="items",
    )
    item_type = models.CharField(
        max_length=20,
        choices=ItemType.choices,
        default=ItemType.DIGITAL,
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items",
    )
    # Flexible attributes/specs (especially useful for digital products)
    attributes = models.JSONField(default=dict, blank=True)

    # Common digital product metadata (optional)
    platform = models.CharField(max_length=120, blank=True)
    region = models.CharField(max_length=80, blank=True)
    language = models.CharField(max_length=80, blank=True)
    license_type = models.CharField(max_length=80, blank=True)
    delivery_method = models.CharField(max_length=80, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "items"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


def item_image_upload_to(instance, filename: str) -> str:
    return f"items/{instance.item_id}/{filename}"


class ItemImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to=item_image_upload_to)
    alt_text = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "item_images"
        ordering = ["sort_order", "created_at"]


class Auction(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        ACTIVE = "active", "Active"
        ENDED = "ended", "Ended"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="auctions",
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name="auctions",
        null=True,
        blank=True,
    )
    starting_price = models.DecimalField(max_digits=12, decimal_places=2)
    current_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reserve_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    start_time = models.DateTimeField(null=True, blank=True, help_text="When auction goes live (can be future)")
    end_time = models.DateTimeField(null=True, blank=True, help_text="When auction ends (computed from start_time + duration)")
    duration_days = models.PositiveIntegerField(default=0, help_text="Duration in days")
    duration_hours = models.PositiveIntegerField(default=0, help_text="Duration in hours")
    duration_minutes = models.PositiveIntegerField(default=0, help_text="Duration in minutes")
    activate_task_id = models.CharField(max_length=255, null=True, blank=True)
    end_task_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "auctions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.item.title} ({self.status})"

    def get_duration_timedelta(self):
        """Return total duration as timedelta."""
        return timedelta(
            days=self.duration_days,
            hours=self.duration_hours,
            minutes=self.duration_minutes,
        )

    def compute_end_time(self):
        """Set end_time = start_time + duration. Call after start_time is set."""
        if self.start_time:
            self.end_time = self.start_time + self.get_duration_timedelta()

    def save(self, *args, **kwargs):
        if not self.current_price:
            self.current_price = self.starting_price
        if self.start_time and (self.duration_days or self.duration_hours or self.duration_minutes):
            self.compute_end_time()
        super().save(*args, **kwargs)


class Watchlist(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="watchlist",
    )
    auction = models.ForeignKey(
        Auction,
        on_delete=models.CASCADE,
        related_name="watchers",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "watchlist"
        unique_together = ["user", "auction"]
