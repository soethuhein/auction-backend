"""
Celery tasks for auctions.
Use with Redis or RabbitMQ as broker.
Schedule via CELERY_BEAT_SCHEDULE in settings.
"""

import logging

from celery import shared_task
from django.utils import timezone

from .broadcasts import broadcast_auction_ended, broadcast_auction_started
from config.celery import app as celery_app


def _revoke_task(task_id):
    """Revoke a previously scheduled Celery task if it exists."""
    if not task_id:
        return
    try:
        celery_app.control.revoke(task_id, terminate=False)
    except Exception:
        # Do not break auction flow if revoke fails.
        pass


def schedule_auction_tasks(auction):
    """
    Schedule precise ETA tasks for auction start/end.
    Existing scheduled tasks are revoked before re-scheduling.
    """
    from .models import Auction

    now = timezone.now()
    _revoke_task(auction.activate_task_id)
    _revoke_task(auction.end_task_id)

    activate_task_id = None
    end_task_id = None

    if (
        auction.status == Auction.Status.SCHEDULED
        and auction.start_time
        and auction.start_time > now
    ):
        try:
            result = activate_auction_at_eta.apply_async(
                args=[str(auction.id)],
                eta=auction.start_time,
            )
            activate_task_id = result.id
        except Exception:
            activate_task_id = None

    if auction.status in (Auction.Status.SCHEDULED, Auction.Status.ACTIVE) and auction.end_time:
        end_eta = auction.end_time if auction.end_time > now else now
        try:
            result = end_auction_at_eta.apply_async(
                args=[str(auction.id)],
                eta=end_eta,
            )
            end_task_id = result.id
        except Exception:
            end_task_id = None

    auction.activate_task_id = activate_task_id
    auction.end_task_id = end_task_id
    auction.save(update_fields=["activate_task_id", "end_task_id", "updated_at"])


@shared_task
def activate_auction_at_eta(auction_id):
    """Activate a scheduled auction exactly at its start_time."""
    logger = logging.getLogger(__name__)
    logger.info("activate_auction_at_eta called with auction_id: %s", auction_id)
    from .models import Auction

    try:
        auction = Auction.objects.get(pk=auction_id)
    except Auction.DoesNotExist:
        return f"Auction {auction_id} not found"

    if auction.status != Auction.Status.SCHEDULED:
        return f"Auction {auction_id} skipped (status={auction.status})"

    now = timezone.now()
    if auction.start_time and auction.start_time > now:
        result = activate_auction_at_eta.apply_async(
            args=[str(auction.id)],
            eta=auction.start_time,
        )
        auction.activate_task_id = result.id
        auction.save(update_fields=["activate_task_id", "updated_at"])
        return f"Auction {auction_id} re-scheduled for {auction.start_time.isoformat()}"

    if not auction.current_price:
        auction.current_price = auction.starting_price
    auction.status = Auction.Status.ACTIVE
    auction.activate_task_id = None
    auction.save(update_fields=["status", "current_price", "activate_task_id", "updated_at"])

    broadcast_auction_started(
        auction.id,
        start_time=auction.start_time,
        end_time=auction.end_time,
        current_price=auction.current_price,
    )
    return f"Auction {auction_id} activated"


@shared_task
def end_auction_at_eta(auction_id):
    """End an auction exactly at its end_time."""
    logger = logging.getLogger(__name__)
    logger.info("end_auction_at_eta called with auction_id: %s", auction_id)
    from .models import Auction

    try:
        auction = Auction.objects.get(pk=auction_id)
    except Auction.DoesNotExist:
        return f"Auction {auction_id} not found"

    if auction.status == Auction.Status.ENDED:
        if auction.end_task_id:
            auction.end_task_id = None
            auction.save(update_fields=["end_task_id", "updated_at"])
        return f"Auction {auction_id} already ended"

    if not auction.end_time:
        return f"Auction {auction_id} has no end_time"

    now = timezone.now()
    if auction.end_time > now:
        result = end_auction_at_eta.apply_async(
            args=[str(auction.id)],
            eta=auction.end_time,
        )
        auction.end_task_id = result.id
        auction.save(update_fields=["end_task_id", "updated_at"])
        return f"Auction {auction_id} re-scheduled for {auction.end_time.isoformat()}"

    auction.status = Auction.Status.ENDED
    auction.activate_task_id = None
    auction.end_task_id = None
    auction.save(update_fields=["status", "activate_task_id", "end_task_id", "updated_at"])

    broadcast_auction_ended(auction.id)
    return f"Auction {auction_id} ended"


@shared_task
def end_expired_auctions():
    """Mark auctions as ended when end_time has passed. Broadcasts to WebSocket."""
    from .models import Auction

    now = timezone.now()
    auction_ids = list(
        Auction.objects.filter(
            status=Auction.Status.ACTIVE,
            end_time__lte=now,
        ).values_list("id", flat=True)
    )
    for aid in auction_ids:
        broadcast_auction_ended(aid)
    updated = Auction.objects.filter(id__in=auction_ids).update(
        status=Auction.Status.ENDED,
        activate_task_id=None,
        end_task_id=None,
    )
    return f"Ended {updated} auctions"


@shared_task
def activate_scheduled_auctions():
    """Activate scheduled auctions when start_time reached. Broadcasts auction_started."""
    from .models import Auction

    now = timezone.now()
    auctions = list(
        Auction.objects.filter(
            status=Auction.Status.SCHEDULED,
            start_time__lte=now,
        )
    )
    # Persist ACTIVE before broadcasting so REST + WS clients see a consistent state (no race).
    for auction in auctions:
        if not auction.current_price:
            auction.current_price = auction.starting_price
        auction.status = Auction.Status.ACTIVE
        auction.activate_task_id = None
        auction.save(
            update_fields=["status", "current_price", "activate_task_id", "updated_at"],
        )
        broadcast_auction_started(
            auction.id,
            start_time=auction.start_time,
            end_time=auction.end_time,
            current_price=auction.current_price,
        )
    return f"Activated {len(auctions)} scheduled auctions"
