# SkyMate - AI Travel Assistant

## Overview
SkyMate is an agentic AI-powered travel assistant that helps users search for flights using natural language. It features:
- Conversational chat interface with real-time responses
- Natural language understanding for travel intent extraction
- Integration with Amadeus Flight Search API for live flight data
- OpenAI GPT-4 powered agentic reasoning with tool calling
- mem0 integration for personalized user preferences
- Beautiful, responsive UI with dark/light mode support

## Architecture

### Frontend (React + TypeScript)
- Located in `client/src/`
- Uses Shadcn UI components with Tailwind CSS
- Key components:
  - `pages/home.tsx` - Main chat page
  - `components/chat/` - Chat interface components
  - `components/theme-provider.tsx` - Dark/light mode support
- State management via TanStack Query

### Backend (Python + Flask)
- Located in `python_backend/`
- Files:
  - `app.py` - Flask server with REST API endpoints
  - `agent.py` - OpenAI-powered agentic loop with tool calling
  - `amadeus_client.py` - Amadeus Flight API integration
  - `memory_manager.py` - mem0 memory management for user preferences

### Express Server (Node.js)
- Located in `server/`
- Acts as a proxy to the Python backend
- Serves the frontend in production

## Running the Application
1. Start the Python backend: `cd python_backend && python app.py`
2. Start the frontend: `npm run dev`

## Environment Variables Required
- `OPENAI_API_KEY` - OpenAI API key for GPT-4
- `AMADEUS_API_KEY` - Amadeus API key
- `AMADEUS_API_SECRET` - Amadeus API secret
- `PYTHON_BACKEND_PORT` - Port for Python backend (default: 5001)
- `PYTHON_BACKEND_URL` - URL for Python backend (default: http://localhost:5001)

## Data Models
See `shared/schema.ts` for TypeScript types:
- `ChatMessage` - Individual chat messages
- `FlightOffer` - Flight search results
- `UserPreferences` - User travel preferences

## Design Guidelines
See `design_guidelines.md` for UI/UX specifications.
