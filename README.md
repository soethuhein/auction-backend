# Auction Backend

Django REST Framework backend for the Auction Management System with support for Redis and RabbitMQ.

## Stack

- **Django 5** + **DRF**
- **MySQL** (recommended for dev) or **PostgreSQL**
- **Redis** (cache, Channels, Celery broker/result)
- **Django Channels** (WebSockets for live bidding)
- **Celery** (async tasks; broker: Redis or RabbitMQ)

## Setup

### 1. Virtual environment

```bash
python -m venv venv
venv\Scripts\activate  # Windows
# or: source venv/bin/activate  # Linux/Mac
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment

Copy `.env.example` to `.env` and adjust variables.

#### MySQL (recommended)
Set these in `.env`:

```env
DB_ENGINE=mysql
DB_NAME=auction_db
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=3306
```

#### SQLite (quick local dev)

```env
DB_ENGINE=sqlite
```

### 4. Database

```bash
# Create your database first, then:
python manage.py migrate
python manage.py createsuperuser
```

### MySQL notes

- Set `DB_ENGINE=mysql` in `.env`
- Use `DB_PORT=3306` (or your custom port)
- Ensure MySQL server is running and database exists before migrations
- If you see auth plugin issues on Windows, use MySQL 8 default auth or configure the user accordingly

### 5. Run

```bash
# HTTP + WebSocket (Daphne)
python manage.py runserver

# Or for production:
# daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

### 6. Celery (required for auto-ending auctions)

**Requires Redis** for broker and Channels (WebSocket broadcast).

**On Windows:** use `-P solo` for the worker (prefork pool has known issues):

```powershell
# Terminal 1 - Worker (use -P solo on Windows)
celery -A config worker -l info -P solo

# Terminal 2 - Beat (runs end_expired_auctions every 60s)
celery -A config beat -l info
```

Or run `.\run_dev.ps1` to start Django + Celery worker + Beat in separate windows.

- `end_expired_auctions` – marks auctions ended when end_time passed, broadcasts `auction_ended` via WebSocket
- `activate_scheduled_auctions` – activates scheduled auctions when start_time reached, broadcasts `auction_started`

## WebSocket events

- `auction_started` – when auction goes live (manual start or scheduled)
- `bid_update` – when a new bid is placed
- `auction_ended` – when auction end_time is reached

## Logging

Logs are written to `logs/`:
- `logs/django.log` – Django request/error logs
- `logs/celery.log` – Celery worker/beat logs
- `logs/app.log` – App logs (auctions, bids, users)

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register/` | Register |
| POST | `/api/auth/login/` | Login (JWT) |
| POST | `/api/auth/refresh/` | Refresh token |
| GET | `/api/auth/me/` | Current user |
| GET | `/api/auth/me/auctions/` | My auctions |
| GET | `/api/auth/me/bids/` | My bids |
| GET | `/api/auth/me/watchlist/` | My watchlist |
| GET | `/api/auctions/` | List auctions |
| POST | `/api/auctions/` | Create auction |
| GET | `/api/auctions/{id}/` | Auction detail |
| PATCH | `/api/auctions/{id}/` | Update auction |
| POST | `/api/auctions/{id}/start/` | Start auction |
| GET | `/api/items/` | List my items |
| POST | `/api/items/` | Create item |
| GET | `/api/items/{id}/` | Item detail |
| PATCH | `/api/items/{id}/` | Update item |
| POST | `/api/items/{id}/upload_image/` | Upload item image (multipart) |
| GET | `/api/items/{id}/images/` | List item images |
| DELETE | `/api/items/{id}/images/{image_id}/` | Delete item image |
| POST | `/api/auctions/{id}/add_to_watchlist/` | Add to watchlist |
| POST | `/api/auctions/{id}/remove_from_watchlist/` | Remove from watchlist |
| POST | `/api/auctions/{id}/bid/` | Place bid |
| GET | `/api/bids/` | My bids |
| GET | `/api/categories/` | List categories |

## WebSocket

- **URL:** `ws://localhost:8000/ws/auctions/{auction_id}/`
- **Purpose:** Live bid updates for active auctions.

## Redis & RabbitMQ

- **Redis:** Used for cache, Channels (WebSocket), and Celery broker/result. Default: `redis://localhost:6379/0`.
- **RabbitMQ:** Optional Celery broker. Set `CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//` in `.env`.

## Celery tasks

- `auctions.tasks.end_expired_auctions` – Mark auctions as ended when `end_time` has passed. Schedule via Celery Beat.

## Testing

```bash
pytest tests/ -v
```

By default, tests run with **SQLite** (fast, isolated). Tests include:
- **Model tests** – User, Category, Auction, Bid, Watchlist
- **Auth tests** – Register, login, refresh, me
- **API tests** – Auctions, bids, categories, watchlist, permissions
