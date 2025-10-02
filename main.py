from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from datetime import datetime
import sqlite3
import secrets
import uvicorn

app = FastAPI(title="API Rate Limiter", version="1.0.0")

# Database setup
def init_db():
    conn = sqlite3.connect('api_limiter.db')
    cursor = conn.cursor()
    
    # Table for storing API keys
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            api_key TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            rate_limit INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')
    
    # Table for storing request logs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            status TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database when app starts
init_db()

# Request/Response models
class RegisterRequest(BaseModel):
    email: str
    rate_limit: int = 100  # default 100 requests per day

class RegisterResponse(BaseModel):
    api_key: str
    email: str
    rate_limit: int
    message: str

class RateLimitResponse(BaseModel):
    current_usage: int
    rate_limit: int
    remaining: int
    status: str

class LogEntry(BaseModel):
    timestamp: str
    endpoint: str
    status: str

# Helper function to generate API key
def generate_api_key():
    return f"sk_{secrets.token_urlsafe(24)}"

# Helper function to get today's date
def get_today():
    return datetime.now().strftime("%Y-%m-%d")

# Helper function to count today's requests
def count_todays_requests(api_key):
    conn = sqlite3.connect('api_limiter.db')
    cursor = conn.cursor()
    
    today = get_today()
    # Count how many times this key was used today
    cursor.execute('''
        SELECT COUNT(*) FROM logs 
        WHERE api_key = ? AND DATE(timestamp) = ?
    ''', (api_key, today))
    
    count = cursor.fetchone()[0]
    conn.close()
    return count

# Helper function to add log entry
def add_log(api_key, endpoint, status):
    conn = sqlite3.connect('api_limiter.db')
    cursor = conn.cursor()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO logs (api_key, timestamp, endpoint, status)
        VALUES (?, ?, ?, ?)
    ''', (api_key, timestamp, endpoint, status))
    
    conn.commit()
    conn.close()

# Endpoint 1: Register a new API key
@app.post("/register", response_model=RegisterResponse)
def register(request: RegisterRequest):
    conn = sqlite3.connect('api_limiter.db')
    cursor = conn.cursor()
    
    # Check if email already exists
    cursor.execute('SELECT email FROM api_keys WHERE email = ?', (request.email,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Generate new API key
    api_key = generate_api_key()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Save to database
    cursor.execute('''
        INSERT INTO api_keys (api_key, email, rate_limit, created_at)
        VALUES (?, ?, ?, ?)
    ''', (api_key, request.email, request.rate_limit, created_at))
    
    conn.commit()
    conn.close()
    
    return RegisterResponse(
        api_key=api_key,
        email=request.email,
        rate_limit=request.rate_limit,
        message="API key created successfully!"
    )

# Endpoint 2: Check rate limit and validate key
@app.get("/check-limit", response_model=RateLimitResponse)
def check_limit(x_api_key: str = Header(...)):
    conn = sqlite3.connect('api_limiter.db')
    cursor = conn.cursor()
    
    # Check if API key exists
    cursor.execute('SELECT rate_limit FROM api_keys WHERE api_key = ?', (x_api_key,))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    rate_limit = result[0]
    current_usage = count_todays_requests(x_api_key)
    
    # Check if user exceeded their limit
    if current_usage >= rate_limit:
        add_log(x_api_key, "/check-limit", "rate_limit_exceeded")
        conn.close()
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Log this successful request
    add_log(x_api_key, "/check-limit", "success")
    conn.close()
    
    remaining = rate_limit - current_usage - 1  # subtract 1 for current request
    
    return RateLimitResponse(
        current_usage=current_usage + 1,
        rate_limit=rate_limit,
        remaining=remaining,
        status="allowed"
    )

# Endpoint 3: Get logs for your API key
@app.get("/logs")
def get_logs(x_api_key: str = Header(...), limit: int = 50):
    conn = sqlite3.connect('api_limiter.db')
    cursor = conn.cursor()
    
    # Verify API key exists
    cursor.execute('SELECT api_key FROM api_keys WHERE api_key = ?', (x_api_key,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Get logs for this key
    cursor.execute('''
        SELECT timestamp, endpoint, status FROM logs
        WHERE api_key = ?
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (x_api_key, limit))
    
    logs = cursor.fetchall()
    conn.close()
    
    # Format logs nicely
    log_entries = [
        LogEntry(timestamp=log[0], endpoint=log[1], status=log[2])
        for log in logs
    ]
    
    return {
        "total_logs": len(log_entries),
        "logs": log_entries
    }

# Basic home endpoint
@app.get("/")
def home():
    return {
        "message": "API Rate Limiter",
        "endpoints": {
            "POST /register": "Register new API key",
            "GET /check-limit": "Check your rate limit (requires X-API-Key header)",
            "GET /logs": "View your usage logs (requires X-API-Key header)"
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
