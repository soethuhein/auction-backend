"""Tests for auction Celery task scheduling and ETA execution."""
from datetime import timedelta

from django.utils import timezone

from auctions import tasks as auction_tasks
from auctions.models import Auction


class _Result:
    def __init__(self, task_id):
        self.id = task_id


class TestAuctionTaskScheduling:
    def test_schedule_auction_tasks_for_scheduled_auction(self, auction, monkeypatch):
        now = timezone.now()
        auction.status = Auction.Status.SCHEDULED
        auction.start_time = now + timedelta(minutes=5)
        auction.end_time = now + timedelta(minutes=65)
        auction.activate_task_id = "old-activate"
        auction.end_task_id = "old-end"
        auction.save()

        revoke_calls = []
        monkeypatch.setattr(
            auction_tasks.celery_app.control,
            "revoke",
            lambda task_id, terminate=False: revoke_calls.append((task_id, terminate)),
        )

        def fake_activate_apply_async(args, eta):
            assert args == [str(auction.id)]
            assert eta == auction.start_time
            return _Result("activate-new")

        def fake_end_apply_async(args, eta):
            assert args == [str(auction.id)]
            assert eta == auction.end_time
            return _Result("end-new")

        monkeypatch.setattr(auction_tasks.activate_auction_at_eta, "apply_async", fake_activate_apply_async)
        monkeypatch.setattr(auction_tasks.end_auction_at_eta, "apply_async", fake_end_apply_async)

        auction_tasks.schedule_auction_tasks(auction)
        auction.refresh_from_db()

        assert ("old-activate", False) in revoke_calls
        assert ("old-end", False) in revoke_calls
        assert auction.activate_task_id == "activate-new"
        assert auction.end_task_id == "end-new"

    def test_schedule_auction_tasks_for_active_auction_schedules_end_only(self, active_auction, monkeypatch):
        now = timezone.now()
        active_auction.start_time = now - timedelta(minutes=5)
        active_auction.end_time = now + timedelta(minutes=20)
        active_auction.activate_task_id = "stale-activate"
        active_auction.end_task_id = None
        active_auction.save()

        revoke_calls = []
        monkeypatch.setattr(
            auction_tasks.celery_app.control,
            "revoke",
            lambda task_id, terminate=False: revoke_calls.append((task_id, terminate)),
        )

        activate_called = {"value": False}
        monkeypatch.setattr(
            auction_tasks.activate_auction_at_eta,
            "apply_async",
            lambda *args, **kwargs: activate_called.__setitem__("value", True),
        )
        monkeypatch.setattr(
            auction_tasks.end_auction_at_eta,
            "apply_async",
            lambda args, eta: _Result("end-only"),
        )

        auction_tasks.schedule_auction_tasks(active_auction)
        active_auction.refresh_from_db()

        assert ("stale-activate", False) in revoke_calls
        assert activate_called["value"] is False
        assert active_auction.activate_task_id is None
        assert active_auction.end_task_id == "end-only"


class TestAuctionETATasks:
    def test_activate_auction_at_eta_activates_and_broadcasts(self, auction, monkeypatch):
        now = timezone.now()
        auction.status = Auction.Status.SCHEDULED
        auction.start_time = now - timedelta(seconds=1)
        auction.end_time = now + timedelta(hours=1)
        auction.current_price = 0
        auction.activate_task_id = "pending-activate"
        auction.save()

        broadcasts = []
        monkeypatch.setattr(
            auction_tasks,
            "broadcast_auction_started",
            lambda auction_id, start_time, end_time, current_price: broadcasts.append(
                (str(auction_id), start_time, end_time, current_price)
            ),
        )

        result = auction_tasks.activate_auction_at_eta.run(str(auction.id))
        auction.refresh_from_db()

        assert "activated" in result
        assert auction.status == Auction.Status.ACTIVE
        assert auction.current_price == auction.starting_price
        assert auction.activate_task_id is None
        assert len(broadcasts) == 1

    def test_activate_auction_at_eta_reschedules_if_early(self, auction, monkeypatch):
        now = timezone.now()
        auction.status = Auction.Status.SCHEDULED
        auction.start_time = now + timedelta(minutes=2)
        auction.end_time = now + timedelta(hours=1)
        auction.save()

        monkeypatch.setattr(
            auction_tasks.activate_auction_at_eta,
            "apply_async",
            lambda args, eta: _Result("activate-rescheduled"),
        )

        result = auction_tasks.activate_auction_at_eta.run(str(auction.id))
        auction.refresh_from_db()

        assert "re-scheduled" in result
        assert auction.status == Auction.Status.SCHEDULED
        assert auction.activate_task_id == "activate-rescheduled"

    def test_end_auction_at_eta_ends_and_broadcasts(self, active_auction, monkeypatch):
        now = timezone.now()
        active_auction.end_time = now - timedelta(seconds=1)
        active_auction.activate_task_id = "some-activate"
        active_auction.end_task_id = "some-end"
        active_auction.save()

        ended = []
        monkeypatch.setattr(
            auction_tasks,
            "broadcast_auction_ended",
            lambda auction_id: ended.append(str(auction_id)),
        )

        result = auction_tasks.end_auction_at_eta.run(str(active_auction.id))
        active_auction.refresh_from_db()

        assert "ended" in result
        assert active_auction.status == Auction.Status.ENDED
        assert active_auction.activate_task_id is None
        assert active_auction.end_task_id is None
        assert ended == [str(active_auction.id)]

    def test_end_auction_at_eta_reschedules_if_early(self, active_auction, monkeypatch):
        now = timezone.now()
        active_auction.end_time = now + timedelta(minutes=3)
        active_auction.save()

        monkeypatch.setattr(
            auction_tasks.end_auction_at_eta,
            "apply_async",
            lambda args, eta: _Result("end-rescheduled"),
        )

        result = auction_tasks.end_auction_at_eta.run(str(active_auction.id))
        active_auction.refresh_from_db()

        assert "re-scheduled" in result
        assert active_auction.status == Auction.Status.ACTIVE
        assert active_auction.end_task_id == "end-rescheduled"
