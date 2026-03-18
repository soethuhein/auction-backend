from django.contrib import admin
from .models import Auction, Category, Watchlist


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    list_display = ("title", "seller", "status", "current_price", "end_time")
    list_filter = ("status", "category")
    search_fields = ("title", "description")


@admin.register(Watchlist)
class WatchlistAdmin(admin.ModelAdmin):
    list_display = ("user", "auction")
