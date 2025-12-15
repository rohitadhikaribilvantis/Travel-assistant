# 🛫 SkyMate - AI Travel Assistant

An intelligent, conversational travel assistant that helps you search for and book flights using natural language. Just tell it where you want to go, and let AI handle the rest!

## ✨ Features

- 🤖 **AI-Powered Chat** - Conversational interface powered by GPT-4
- 🔍 **Smart Flight Search** - Natural language flight discovery via Amadeus API
- 💾 **Memory** - Remembers your preferences using mem0 AI
- 🎨 **Modern UI** - Beautiful dark/light mode support with responsive design
- 🔐 **Secure Authentication** - JWT-based user accounts with bcrypt encryption
- 💬 **Conversation History** - Save and revisit past flight searches
- ⚡ **Fast & Async** - Built with FastAPI for high performance

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- npm or yarn

### Installation

1. **Clone/Setup the project**
```bash
cd Travel-assistant
```

2. **Create Python virtual environment**
```bash
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# macOS/Linux (bash)
python3 -m venv .venv
source .venv/bin/activate
```

3. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

4. **Install frontend dependencies**
```bash
cd client
npm install
cd ..
```

5. **Setup environment variables**
```bash
# Copy the example file to create your .env
cd server
cp .env.example .env
cd ..
```

Then edit `server/.env` and fill in your API keys:
- **OPENAI_API_KEY** - Get from [OpenAI Platform](https://platform.openai.com/api-keys)
- **AMADEUS_API_KEY & AMADEUS_API_SECRET** - Get from [Amadeus for Developers](https://developers.amadeus.com/)
- **JWT_SECRET** - Use any random string for development
- **MEM0_API_KEY** - Optional, get from [mem0](https://mem0.ai/) (leave as is if not using)

6. **Install backend database support**
```bash
pip install sqlalchemy
```

### Environment Variables Setup

Quick setup on different OS:

**Windows (PowerShell):**
```powershell
cd server
Copy-Item .env.example .env
# Then edit .env with your API keys
```

**macOS/Linux:**
```bash
cd server
cp .env.example .env
# Then edit .env with your API keys
nano .env
```

### Running the Application

**Terminal 1 - Start Backend:**
```bash
python server/main.py
```
Backend runs on http://localhost:8000

**Terminal 2 - Start Frontend:**
```bash
cd client
npm run dev
```
Frontend runs on http://localhost:5173

**Open your browser:** http://localhost:5173

## 📚 Documentation

- **[QUICKSTART.md](./QUICKSTART.md)** - Get started in 5 minutes
- **[API_REFERENCE.md](./API_REFERENCE.md)** - Complete API endpoints
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - System design overview
- **[MIGRATION_FASTAPI.md](./MIGRATION_FASTAPI.md)** - Backend migration details

## 🏗️ Project Structure

```
Travel-assistant/
├── client/                    # React Frontend
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── hooks/            # Custom hooks (auth, chat)
│   │   ├── pages/            # Page components
│   │   ├── lib/              # Utilities
│   │   └── App.tsx           # Main app
│   └── package.json
│
├── server/                   # Backend (FastAPI)
│   ├── main.py              # FastAPI application ⭐
│   ├── agent.py             # AI agent logic
│   ├── amadeus_client.py    # Flight search API
│   └── memory_manager.py    # User preferences
│
├── requirements.txt         # Python dependencies
├── ARCHITECTURE.md          # System design
└── README.md               # This file
```

## 🔌 API Endpoints

### Authentication
- `POST /api/auth/register` - Create account
- `POST /api/auth/login` - Login
- `GET /api/auth/me` - Get current user
- `PUT /api/auth/profile` - Update profile

### Chat
- `POST /api/chat` - Send chat message
- `GET /api/conversations` - List conversations
- `GET /api/conversations/{id}` - Get conversation

### System
- `GET /api/health` - Health check
- `GET /docs` - Swagger UI (interactive API testing)

## 🛠️ Tech Stack

### Frontend
- **React 18** - UI library
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Shadcn UI** - Component library
- **TanStack Query** - Data fetching
- **Next-themes** - Dark mode

### Backend
- **FastAPI** - Modern Python web framework
- **Uvicorn** - ASGI server
- **Pydantic** - Data validation
- **JWT** - Authentication
- **Bcrypt** - Password hashing
- **OpenAI** - AI/GPT-4
- **Amadeus SDK** - Flight search
- **mem0** - User memory

## 🔐 Authentication

1. Register or login via frontend
2. Receive JWT token
3. Token stored in localStorage
4. All requests include `Authorization: Bearer <token>` header
5. Server validates token on each request

## 📖 Example Usage

### Register
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "user",
    "password": "Password123!",
    "fullName": "John Doe"
  }'
```

### Chat
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "message": "Find me flights from NYC to LA tomorrow"
  }'
```

## 🧪 Testing

### Using Swagger UI
Visit http://localhost:8000/docs for interactive API testing

### Using cURL
See examples above or check [API_REFERENCE.md](./API_REFERENCE.md)

### Using Frontend
1. Open http://localhost:5173
2. Register/Login
3. Type messages to search for flights

## 🔄 Development

### Backend Development
```bash
# Run with auto-reload
uvicorn server.main:app --reload --port 8000

# Run with debug logging
python server/main.py
```

### Frontend Development
```bash
cd client
npm run dev    # Start dev server with hot reload
npm run build  # Build for production
```


### Using Railway/Render
See deployment documentation for each platform.

## 🐛 Troubleshooting

### Backend won't start
```bash
# Check Python version
python --version  # Should be 3.9+

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check port availability
lsof -i :8000
```

### Frontend won't connect
- Ensure backend is running on port 8000
- Check browser console for CORS errors
- Verify `Authorization` header is being sent

### API key errors
- Verify keys are set: `echo $OPENAI_API_KEY`
- Check keys have required permissions
- Check for billing/quota issues on API provider

### Token issues
- Try logging out and back in
- Check token format in DevTools
- Verify `JWT_SECRET` env var is set

## 📝 Environment Variables

```bash
# Required
OPENAI_API_KEY           # OpenAI API key
AMADEUS_API_KEY          # Amadeus API key
AMADEUS_API_SECRET       # Amadeus API secret
JWT_SECRET               # Any random string for JWT

# Optional
PYTHON_BACKEND_PORT=8000 # Backend port (default: 8000)
NODE_ENV=development     # Environment (default: development)
```

