# API Rate Limiter

A simple REST API that manages API keys and enforces daily rate limits. Built this to learn FastAPI and practice working with databases.

## What it does

If you're running an API service, you need a way to control who accesses it and how often. This project handles that by:
- Giving each user a unique API key when they register
- Tracking how many requests each key makes per day
- Blocking requests after the daily limit is hit
- Keeping logs of everything for monitoring

Think of it as a gatekeeper for your API.

## Tech used

- FastAPI (for the REST API)
- SQLite (for storing keys and logs)
- Python 3.9+

## Getting started

Clone the repo and install dependencies:

```bash
git clone https://github.com/yourusername/api-rate-limiter.git
cd api-rate-limiter

python -m venv venv
source venv/bin/activate  # on Windows: venv\Scripts\activate

pip install -r requirements.txt
python main.py
```

Server runs on `http://localhost:8000`

Check out the interactive docs at `http://localhost:8000/docs`

## How to use it

### Register and get an API key

```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "rate_limit": 100}'
```

You'll get back something like:
```json
{
  "api_key": "sk_xxxxxxxxxx",
  "email": "test@example.com",
  "rate_limit": 100,
  "message": "API key created successfully!"
}
```

Save that API key - you'll need it for other requests.

### Check your rate limit

```bash
curl -X GET http://localhost:8000/check-limit \
  -H "X-API-Key: sk_your_key_here"
```

Response:
```json
{
  "current_usage": 23,
  "rate_limit": 100,
  "remaining": 77,
  "status": "allowed"
}
```

Once you hit your limit, you'll get a 429 error.

### View your logs

```bash
curl -X GET http://localhost:8000/logs \
  -H "X-API-Key: sk_your_key_here"
```

Shows you all your API activity with timestamps.

## Project structure

```
api-rate-limiter/
├── main.py              # Everything is here
├── requirements.txt     # Just 3 dependencies
├── api_limiter.db      # SQLite database (created automatically)
└── README.md
```

Kept it simple - the whole API is in one file.

## How rate limiting works

The system counts requests per day (resets at midnight UTC). When you make a request:

1. Checks if your API key is valid
2. Counts how many times you've used it today
3. If under limit → allows request and logs it
4. If over limit → returns 429 error

The daily reset happens automatically because we only count logs from today's date.

## Database schema

Two tables:

**api_keys**
- api_key (unique)
- email
- rate_limit
- created_at

**logs**
- id
- api_key
- timestamp
- endpoint
- status

## Testing

I tested this manually with Postman and curl. Here's what I checked:

- ✅ Register with new email works
- ✅ Can't register same email twice
- ✅ Rate limit blocks after hitting quota
- ✅ Invalid API keys return 401
- ✅ Logs show all activity
- ✅ Rate resets at midnight

## Things I'd add for production

Right now it's pretty basic, but functional. For a production system I'd add:

- Replace SQLite with PostgreSQL for better concurrency
- Add Redis for caching rate limit counts
- Admin dashboard to manage all keys
- API key deletion/regeneration
- HTTPS and proper security headers
- Better error messages
- Rate limit per hour/minute instead of just daily

But for learning purposes and demos, this works great.

## What I learned

This was a good project for practicing:
- REST API design
- Database integration
- Authentication with headers
- Error handling (401, 429 status codes)
- Git workflow with feature branches

## Running tests

No formal test suite, but you can test manually:

```bash
# Register a key with low limit
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@test.com", "rate_limit": 3}'

# Use the key 3 times (should work)
curl -X GET http://localhost:8000/check-limit -H "X-API-Key: YOUR_KEY"
curl -X GET http://localhost:8000/check-limit -H "X-API-Key: YOUR_KEY"
curl -X GET http://localhost:8000/check-limit -H "X-API-Key: YOUR_KEY"

# 4th request should fail with 429
curl -X GET http://localhost:8000/check-limit -H "X-API-Key: YOUR_KEY"
```

