from django.contrib import admin
from .models import Auction, Category, Watchlist, Item, ItemImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    list_display = ("item", "seller", "status", "current_price", "end_time")
    list_filter = ("status", "item__category")
    search_fields = ("item__title", "item__description")


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "item_type", "category", "created_at")
    list_filter = ("item_type", "category")
    search_fields = ("title", "description")


@admin.register(ItemImage)
class ItemImageAdmin(admin.ModelAdmin):
    list_display = ("item", "sort_order", "created_at")


@admin.register(Watchlist)
class WatchlistAdmin(admin.ModelAdmin):
    list_display = ("user", "auction")
