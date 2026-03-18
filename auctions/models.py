import uuid
from datetime import timedelta
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone


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
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="auctions",
    )
    starting_price = models.DecimalField(max_digits=12, decimal_places=2)
    current_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reserve_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    image_urls = models.JSONField(default=list, blank=True)
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
        return self.title

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
