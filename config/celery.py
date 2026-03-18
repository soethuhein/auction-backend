"""
Celery configuration for auction-backend.
Uses Redis by default; set CELERY_BROKER_URL=amqp://... for RabbitMQ.
"""
from celery import Celery
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("auction")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
