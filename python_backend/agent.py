import os
import json
import re
from datetime import datetime, timedelta
from typing import Optional
from openai import OpenAI
from amadeus_client import amadeus_client
from memory_manager import memory_manager

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_flights",
            "description": "Search for available flights between two airports. Use this when the user wants to find flights.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {
                        "type": "string",
                        "description": "Origin airport IATA code (e.g., 'JFK', 'LAX', 'LHR')"
                    },
                    "destination": {
                        "type": "string",
                        "description": "Destination airport IATA code (e.g., 'CDG', 'DXB', 'NRT')"
                    },
                    "departure_date": {
                        "type": "string",
                        "description": "Departure date in YYYY-MM-DD format"
                    },
                    "return_date": {
                        "type": "string",
                        "description": "Return date in YYYY-MM-DD format (optional, for round trip)"
                    },
                    "adults": {
                        "type": "integer",
                        "description": "Number of adult passengers (default 1)"
                    },
                    "travel_class": {
                        "type": "string",
                        "enum": ["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"],
                        "description": "Cabin class preference"
                    },
                    "non_stop": {
                        "type": "boolean",
                        "description": "Set to true to search only for direct flights"
                    }
                },
                "required": ["origin", "destination", "departure_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remember_preference",
            "description": "Store a user travel preference for future reference. Use this when the user expresses a strong preference.",
            "parameters": {
                "type": "object",
                "properties": {
                    "preference": {
                        "type": "string",
                        "description": "The preference to remember (e.g., 'prefers window seats', 'avoids red-eye flights')"
                    }
                },
                "required": ["preference"]
            }
        }
    }
]

SYSTEM_PROMPT = """You are SkyMate, a friendly and helpful AI travel assistant. You help users find flights, plan trips, and provide travel advice.

Your capabilities:
1. Search for flights using the search_flights tool
2. Remember user preferences using the remember_preference tool
3. Provide travel advice and recommendations

Guidelines:
- Be conversational, warm, and helpful
- When users ask for flights, extract the necessary details (origin, destination, dates, passengers)
- If information is missing, ask clarifying questions naturally
- Use IATA airport codes for searches (help users find the right codes if needed)
- When presenting flight results, highlight the best options and explain trade-offs
- Remember user preferences and apply them to future searches
- If searching for dates, calculate proper YYYY-MM-DD format dates based on today's date

Common city to IATA code mappings:
- New York: JFK, LGA, EWR
- Los Angeles: LAX
- London: LHR, LGW, STN
- Paris: CDG, ORY
- Tokyo: NRT, HND
- Dubai: DXB
- Singapore: SIN
- San Francisco: SFO
- Chicago: ORD
- Miami: MIA
- Boston: BOS
- Seattle: SEA
- Atlanta: ATL
- Dallas: DFW
- Denver: DEN
- Las Vegas: LAS
- Bangalore: BLR
- Mumbai: BOM
- Delhi: DEL

Today's date is {today}.

When you successfully search for flights, format your response to be clear and helpful. Mention any user preferences you're applying to the search.
"""

def get_system_prompt_with_memory(user_id: str) -> str:
    """Get system prompt enriched with user memories."""
    base_prompt = SYSTEM_PROMPT.format(today=datetime.now().strftime("%Y-%m-%d"))
    
    preferences = memory_manager.get_preferences_summary(user_id)
    
    if preferences:
        base_prompt += f"\n\n{preferences}"
    
    return base_prompt

def parse_relative_date(date_text: str) -> Optional[str]:
    """Parse relative date expressions like 'next week', 'tomorrow', etc."""
    today = datetime.now()
    date_text = date_text.lower().strip()
    
    if "tomorrow" in date_text:
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    elif "next week" in date_text:
        return (today + timedelta(weeks=1)).strftime("%Y-%m-%d")
    elif "next month" in date_text:
        return (today + timedelta(days=30)).strftime("%Y-%m-%d")
    elif "in" in date_text and "days" in date_text:
        match = re.search(r"in\s+(\d+)\s+days?", date_text)
        if match:
            days = int(match.group(1))
            return (today + timedelta(days=days)).strftime("%Y-%m-%d")
    elif "in" in date_text and "week" in date_text:
        match = re.search(r"in\s+(\d+)\s+weeks?", date_text)
        if match:
            weeks = int(match.group(1))
            return (today + timedelta(weeks=weeks)).strftime("%Y-%m-%d")
    
    return None

def execute_tool(tool_name: str, arguments: dict, user_id: str) -> dict:
    """Execute a tool and return the result."""
    
    if tool_name == "search_flights":
        origin = arguments.get("origin", "").upper()
        destination = arguments.get("destination", "").upper()
        departure_date = arguments.get("departure_date")
        return_date = arguments.get("return_date")
        adults = arguments.get("adults", 1)
        travel_class = arguments.get("travel_class")
        non_stop = arguments.get("non_stop", False)
        
        result = amadeus_client.search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            adults=adults,
            travel_class=travel_class,
            non_stop=non_stop
        )
        
        if result.get("error"):
            return {"error": result["error"], "flights": []}
        
        flights = result.get("data", [])
        tagged_flights = amadeus_client.tag_flight_offers(flights)
        
        return {"flights": tagged_flights, "count": len(tagged_flights)}
    
    elif tool_name == "remember_preference":
        preference = arguments.get("preference", "")
        messages = [
            {"role": "user", "content": f"I {preference}"},
            {"role": "assistant", "content": f"I'll remember that you {preference}."}
        ]
        memory_manager.add_memory(user_id, messages)
        return {"success": True, "preference": preference}
    
    return {"error": "Unknown tool"}

def process_message(user_message: str, user_id: str = "default-user", conversation_history: list = None) -> dict:
    """
    Process a user message and generate a response.
    
    Args:
        user_message: The user's message
        user_id: The user identifier
        conversation_history: Previous messages in the conversation
        
    Returns:
        dict with 'content' (str) and optionally 'flight_results' (list)
    """
    if conversation_history is None:
        conversation_history = []
    
    system_prompt = get_system_prompt_with_memory(user_id)
    
    messages = [{"role": "system", "content": system_prompt}]
    
    for msg in conversation_history[-10:]:
        messages.append({
            "role": msg.get("role", "user"),
            "content": msg.get("content", "")
        })
    
    messages.append({"role": "user", "content": user_message})
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=2048
        )
        
        assistant_message = response.choices[0].message
        flight_results = []
        memory_context = None
        
        if assistant_message.tool_calls:
            tool_results = []
            
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                
                result = execute_tool(tool_name, arguments, user_id)
                tool_results.append({
                    "tool_call_id": tool_call.id,
                    "output": json.dumps(result)
                })
                
                if tool_name == "search_flights" and result.get("flights"):
                    flight_results = result["flights"]
                
                if tool_name == "remember_preference":
                    memory_context = f"Noted: {result.get('preference', '')}"
            
            messages.append({
                "role": "assistant",
                "content": assistant_message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in assistant_message.tool_calls
                ]
            })
            
            for tr in tool_results:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tr["tool_call_id"],
                    "content": tr["output"]
                })
            
            final_response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=2048
            )
            
            final_content = final_response.choices[0].message.content
            
            memory_manager.extract_and_store_preferences(user_id, user_message, final_content)
            
            preferences = memory_manager.get_preferences_summary(user_id)
            if preferences:
                memory_context = "Using your preferences"
            
            return {
                "content": final_content,
                "flight_results": flight_results,
                "memory_context": memory_context
            }
        
        content = assistant_message.content or "I'm sorry, I couldn't generate a response."
        
        memory_manager.extract_and_store_preferences(user_id, user_message, content)
        
        return {
            "content": content,
            "flight_results": [],
            "memory_context": None
        }
        
    except Exception as e:
        return {
            "content": f"I apologize, but I encountered an error while processing your request: {str(e)}. Please try again.",
            "flight_results": [],
            "memory_context": None
        }
