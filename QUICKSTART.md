# Quick Start: FastAPI Backend

## Installation

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Set environment variables
export OPENAI_API_KEY="sk-..."
export AMADEUS_API_KEY="your-key"
export AMADEUS_API_SECRET="your-secret"
export JWT_SECRET="choose-a-secure-random-string"
export PYTHON_BACKEND_PORT=8000
```

## Running the Backend

```bash
# Option 1: Direct Python
python server/main.py

# Option 2: Uvicorn with reload (development)
uvicorn server.main:app --reload --port 8000

# Option 3: Uvicorn with workers (production)
uvicorn server.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Running the Frontend

```bash
cd client
npm install
npm run dev
```

Then open http://localhost:5173 (or whatever port Vite uses)

## Testing Endpoints

```bash
# Health check
curl http://localhost:8000/api/health

# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "Test123!",
    "fullName": "Test User"
  }'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test123!"
  }'

# Get user (requires token)
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Send chat message (requires token)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "message": "Find me flights from NYC to LA tomorrow"
  }'
```

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Key Differences from Old Backend

1. **Port**: Was 5000/5001, now 8000
2. **Framework**: Was Express + Flask, now FastAPI
3. **Authentication**: All routes except auth require Bearer token
4. **Data Format**: Same JSON format, but cleaner error responses

## Troubleshooting

### ModuleNotFoundError: No module named 'fastapi'
```bash
pip install -r requirements.txt
```

### Port 8000 already in use
```bash
# Find and kill process
lsof -i :8000
kill -9 <PID>

# Or change port
export PYTHON_BACKEND_PORT=8001
```

### Invalid token errors
- Make sure you're including: `Authorization: Bearer <token>`
- Token is from login/register response
- Check token is not expired (7 day expiry)

### Agent/OpenAI errors
- Verify API keys are set correctly
- Check OpenAI account has credits
- Make sure `agent.py` and `amadeus_client.py` exist

## File Structure

```
server/
├── main.py           ← FastAPI app (NEW)
├── app.py            ← Old Flask app (deprecated)
├── agent.py          ← AI agent logic
├── amadeus_client.py ← Flight search
└── memory_manager.py ← User preferences
```

## Development Tips

1. Use `--reload` flag for auto-reload on code changes
2. Check Swagger UI at `/docs` for interactive testing
3. Check server logs for detailed error messages
4. Use curl or Postman for API testing
5. Frontend should be on different port (Vite default: 5173)

## Production Deployment

```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn python_backend.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --port 8000
```

Or use Docker (create Dockerfile for containerization).
