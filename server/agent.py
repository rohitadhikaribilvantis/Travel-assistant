import os
import json
import re
from datetime import datetime, timedelta
from typing import Optional
from openai import OpenAI
from amadeus_client import amadeus_client
from memory_manager import memory_manager

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def extract_preferences_from_message(user_message: str) -> list[str]:
    """Extract detailed preference statements from user messages."""
    preferences = []
    message_lower = user_message.lower()
    
    # Seat preferences
    seat_patterns = [
        (r"(?:i\s+)?(?:prefer|want|need)\s+(?:window|aisle|exit\s+row)\s+seats?", "window/aisle/exit row"),
        (r"(?:no|avoid|don't\s+like|hate)\s+(?:middle|center)\s+seats?", "avoid middle seats"),
        (r"(?:window|aisle|exit\s+row)\s+seats?", "window/aisle/exit row seats"),
    ]
    
    # Airline preferences
    airline_patterns = [
        (r"(?:i\s+)?(?:prefer|fly|love)\s+(?:with\s+)?(?:united|american|delta|southwest|jetblue|alaska|spirit|frontier|southwest)", "preferred airline"),
        (r"(?:avoid|don't\s+like|hate)\s+(?:united|american|delta|southwest|jetblue|alaska|spirit|frontier)", "avoid airline"),
    ]
    
    # Time preferences
    time_patterns = [
        (r"(?:early\s+)?morning\s+flights?", "early morning flights"),
        (r"late\s+evening\s+flights?", "late evening flights"),
        (r"afternoon\s+flights?", "afternoon flights"),
        (r"(?:prefer|want)\s+(?:early|late|morning|afternoon|evening)\s+departures?", "preferred departure time"),
    ]
    
    # Flight type preferences
    flight_patterns = [
        (r"(?:find|search\s+for|want|need)?\s*direct\s+flights?", "direct flights"),
        (r"non-?stop\s+(?:only|flights|preferred)?", "non-stop flights"),
        (r"(?:no|avoid)\s+layovers?", "avoid layovers"),
        (r"(?:don't\s+)?(?:mind|ok\s+with)\s+(?:one|1|multiple|some)?\s*layovers?", "willing to take layovers"),
    ]
    
    # Passenger preferences
    passenger_patterns = [
        (r"(?:i\s+)?(?:travel\s+)?(?:alone|solo)", "traveling alone"),
        (r"(?:with\s+)?(?:family|kids|children)", "traveling with family"),
        (r"(?:with\s+)?(?:partner|spouse|significant\s+other)", "traveling with partner"),
    ]
    
    # Baggage preferences
    baggage_patterns = [
        (r"(?:light\s+)?packer|minimal\s+baggage", "light packer"),
        (r"(?:need|require)\s+(?:extra|checked)\s+baggage", "extra baggage needed"),
        (r"cabin\s+baggage\s+only", "carry-on only"),
    ]
    
    # Budget preferences
    budget_patterns = [
        (r"(?:budget|cheap|low\s+cost)", "budget conscious"),
        (r"(?:luxury|premium|first\s+class|business\s+class)", "luxury travel"),
    ]
    
    # Location/home preferences
    location_patterns = [
        (r"(?:i\s+)?(?:live|based|from)\s+(?:in\s+)?(\w+)", "home city prefere, location_patternsnce"),
    ]
    
    all_patterns = [
        seat_patterns, airline_patterns, time_patterns, 
        flight_patterns, passenger_patterns, baggage_patterns, budget_patterns
    ]
    
    for pattern_group in all_patterns:
        for pattern, label in pattern_group:
            if re.search(pattern, message_lower):
                preferences.append(label)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_prefs = []
    for pref in preferences:
        if pref not in seen:
            seen.add(pref)
            unique_prefs.append(pref)
    
    return unique_prefs

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

CRITICAL - TOOL USAGE:
- When the user asks for flights or mentions a destination, IMMEDIATELY call search_flights
- DO NOT say "I'll search for flights" without actually calling the tool in the same response
- If you mention performing a search, you MUST call search_flights in that same response
- When a user expresses a NEW preference (e.g., "I prefer morning flights") AND there is a previous flight search context in the conversation, IMMEDIATELY re-search using the updated preference

MEMORY & PREFERENCES (CRITICAL):
- You have access to the user's stored preferences at the start of every conversation
- ALWAYS retrieve and use stored preferences automatically - DO NOT ask for information you already have
- When presenting flights, MENTION which preferences you're applying (e.g., "Since you prefer direct flights and economy class...")
- When user expresses a NEW preference, CONFIRM it immediately: "Got it, I'll avoid red-eye flights in future searches"
- Store preferences like: seat type (window/aisle), airlines, stops, departure times, cabin class, and red-eye aversion

CABIN CLASS - IMPORTANT:
- If the user is asking to search for flights but has NOT selected/mentioned a cabin class preference, you MUST ask them which cabin class they prefer BEFORE searching
- Offer options: "Would you like Economy, Premium Economy, Business, or First Class?"
- Once they specify, store it as a preference and then search
- If they have a stored cabin class preference, use it automatically without asking

Guidelines:
- Be conversational, warm, and helpful
- Extract necessary flight details: origin, destination, dates, passengers
- If information is missing AND NOT in stored preferences, ask clarifying questions
- If information IS in stored preferences, use it without asking
- Use IATA airport codes for searches
- When presenting flight results, highlight best/cheapest/fastest options
- Remember preferences and apply them AUTOMATICALLY to all future searches
- NEVER ask for cabin class if it's stored - use it automatically
- NEVER ask for passenger count if it's stored - use it automatically  
- NEVER ask for flight type if direct/non-stop preference is stored - use it automatically

When user asks for "direct flights", ALWAYS set the non_stop parameter to true in search_flights tool.
When user expresses red-eye aversion, CONFIRM: "Got it, I'll avoid red-eye flights for you"

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
- Houston: IAH

Today's date is {today}.

When you successfully search for flights, format your response to be clear and helpful. ALWAYS mention any stored preferences you're applying to the search.
"""

def get_system_prompt_with_memory(user_id: str) -> str:
    """Get system prompt enriched with user memories at conversation start."""
    base_prompt = SYSTEM_PROMPT.format(today=datetime.now().strftime("%Y-%m-%d"))
    
    # Retrieve comprehensive user context from memories
    try:
        user_context = memory_manager.get_user_context(user_id)
        pref_summary = memory_manager.summarize_preferences(user_id)
        
        if user_context or pref_summary:
            base_prompt += "\n\n" + "="*70
            base_prompt += "\n📌 YOUR STORED PREFERENCES (Apply These Automatically):\n" + "="*70
            
            # Display preferences in a clear, categorized format
            if pref_summary:
                for category, items in pref_summary.items():
                    if items:
                        category_display = {
                            "seat_preferences": "🪑 Seat Preferences",
                            "airline_preferences": "✈️ Preferred Airlines",
                            "time_preferences": "🕐 Time Preferences",
                            "flight_type_preferences": "🛫 Flight Type",
                            "cabin_class_preferences": "🎫 Cabin Class",
                            "red_eye_preferences": "🌙 Red-Eye Preferences",
                            "passenger_preferences": "👥 Number of Passengers",
                            "baggage_preferences": "🎒 Baggage",
                            "routes": "🗺️ Favorite Routes",
                            "budget_info": "💰 Budget",
                            "location": "📍 Home Location",
                            "other_preferences": "📋 Other"
                        }
                        display_name = category_display.get(category, category.replace("_", " ").title())
                        base_prompt += f"\n{display_name}:\n"
                        for item in items:
                            if isinstance(item, dict):
                                item_text = item.get("text", item.get("memory", str(item)))
                            else:
                                item_text = str(item)
                            base_prompt += f"  • {item_text}\n"
            
            base_prompt += "\n" + "="*70
            base_prompt += "\n✓ USE THESE PREFERENCES AUTOMATICALLY IN ALL SEARCHES"
            base_prompt += "\n✓ MENTION THEM WHEN APPLYING (e.g., 'Since you prefer direct flights...')"
            base_prompt += "\n✓ CONFIRM NEW PREFERENCES IMMEDIATELY WHEN EXPRESSED"
            base_prompt += "\n" + "="*70 + "\n"
    except Exception as e:
        print(f"[ERROR] Error enriching prompt with memory: {e}")
    
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

def get_preference_overrides(user_id: str) -> dict:
    """
    Get flight search parameter overrides from stored preferences.
    
    Returns:
        dict with keys like 'adults', 'travel_class', 'non_stop' if preferences exist
    """
    overrides = {}
    applied_prefs = []
    
    try:
        prefs = memory_manager.summarize_preferences(user_id)
        print(f"[PREFS DEBUG] Summarized preferences for user {user_id}: {prefs}")
        
        # Check for passenger preferences
        if prefs.get("seat_preferences"):
            seat_text = " ".join([str(item) for item in prefs["seat_preferences"]]).lower()
            print(f"[PREFS DEBUG] Seat preferences found: {seat_text}")
            if "alone" in seat_text or "solo" in seat_text:
                overrides["adults"] = 1
                applied_prefs.append("traveling alone")
            elif "2" in seat_text or "couple" in seat_text:
                overrides["adults"] = 2
                applied_prefs.append("2 passengers")
            elif "family" in seat_text or "kids" in seat_text or "children" in seat_text:
                overrides["adults"] = 4  # family default
                applied_prefs.append("family travel")
        
        # Check for cabin class preferences - improved matching
        if prefs.get("cabin_class_preferences"):
            cabin_text = " ".join([str(item) for item in prefs["cabin_class_preferences"]]).lower()
            print(f"[PREFS DEBUG] Cabin class preferences found: {cabin_text}")
            # Check in order of priority to avoid false matches
            if "first" in cabin_text and "class" in cabin_text:
                overrides["travel_class"] = "FIRST"
                applied_prefs.append("First Class preference")
            elif "business" in cabin_text:
                overrides["travel_class"] = "BUSINESS"
                applied_prefs.append("Business Class preference")
            elif "premium" in cabin_text:
                overrides["travel_class"] = "PREMIUM_ECONOMY"
                applied_prefs.append("Premium Economy preference")
            elif "economy" in cabin_text:
                overrides["travel_class"] = "ECONOMY"
                applied_prefs.append("Economy preference")
        else:
            print(f"[PREFS DEBUG] No cabin class preferences stored for user {user_id}")
        
        # Check for direct flight preferences
        if prefs.get("flight_type_preferences"):
            flight_text = " ".join([str(item) for item in prefs["flight_type_preferences"]]).lower()
            print(f"[PREFS DEBUG] Flight type preferences found: {flight_text}")
            if "direct" in flight_text or "non-stop" in flight_text:
                overrides["non_stop"] = True
                applied_prefs.append("direct/non-stop preference")
        
        # Check for time/departure preferences
        if prefs.get("time_preferences") or prefs.get("departure_time"):
            time_prefs = prefs.get("time_preferences", []) or prefs.get("departure_time", [])
            time_text = " ".join([str(item) for item in time_prefs]).lower()
            print(f"[PREFS DEBUG] Time preferences found: {time_text}")
            if time_text:
                overrides["time_preference"] = time_text
                if "morning" in time_text:
                    applied_prefs.append("morning flights")
                elif "afternoon" in time_text:
                    applied_prefs.append("afternoon flights")
                elif "evening" in time_text:
                    applied_prefs.append("evening flights")
                else:
                    applied_prefs.append(f"time preference: {time_text}")
        
        overrides["applied_prefs_summary"] = " & ".join(applied_prefs) if applied_prefs else None
        print(f"[PREFS] Extracted overrides for user {user_id}: {overrides}")
        return overrides
    except Exception as e:
        print(f"[PREFS ERROR] Error extracting preference overrides: {e}")
        import traceback
        traceback.print_exc()
        return {}
        return {}

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
        
        # Ensure non_stop is a boolean (handle string values from JSON)
        if isinstance(non_stop, str):
            non_stop = non_stop.lower() in ("true", "yes", "1")
        
        # Apply preference overrides
        overrides = get_preference_overrides(user_id)
        adults = overrides.get("adults", adults)
        travel_class = overrides.get("travel_class", travel_class)
        non_stop = overrides.get("non_stop", non_stop)
        
        print(f"[FLIGHT] After applying preferences: adults={adults}, class={travel_class}, non_stop={non_stop} (type={type(non_stop)})")
        
        print(f"[FLIGHT SEARCH] origin={origin}, destination={destination}, date={departure_date}")
        
        try:
            result = amadeus_client.search_flights(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                return_date=return_date,
                adults=adults,
                travel_class=travel_class,
                non_stop=non_stop
            )
            
            print(f"[FLIGHT SEARCH] Result: {result}")
            
            if result.get("error"):
                print(f"[FLIGHT SEARCH] Error: {result['error']}")
                return {"error": result["error"], "flights": []}
            
            flights = result.get("data", [])
            tagged_flights = amadeus_client.tag_flight_offers(flights)
            
            print(f"[FLIGHT SEARCH] Found {len(tagged_flights)} flights")
            return {"flights": tagged_flights, "count": len(tagged_flights)}
        except Exception as e:
            print(f"[FLIGHT SEARCH] Exception: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": str(e), "flights": []}
    
    elif tool_name == "remember_preference":
        preference = arguments.get("preference", "")
        print(f"[PREF] Storing preference: {preference}")
        
        # Store the preference directly
        result = memory_manager.add_structured_memory(
            user_id=user_id,
            category="preference",
            content=preference,
            memory_type="general",
            metadata={"extracted_at": datetime.now().isoformat()}
        )
        
        return {
            "success": True,
            "preference": preference,
            "stored": bool(result),
            "confirmation": f"I'll remember: {preference}"
        }
    
    return {"error": "Unknown tool"}

def _merge_preferences(stored_prefs: dict, current_prefs: dict) -> dict:
    """
    Merge stored preferences (from mem0) with current UI preferences.
    Current preferences take priority as they're the latest selections.
    """
    import random
    
    # Varied phrasings to avoid repetition
    phrasings = [
        lambda x: f"Prefers {x}",
        lambda x: f"Likes {x}",
        lambda x: f"Interested in {x}",
        lambda x: f"Looking for {x}",
        lambda x: f"Going for {x}",
    ]
    
    merged = {}
    
    # Add all stored preferences
    for category, items in stored_prefs.items():
        if items:
            merged[category] = items
    
    # Add/override with current UI preferences
    phrasing_func = random.choice(phrasings)
    
    if current_prefs.get("directFlightsOnly"):
        if "flight_type_preferences" not in merged:
            merged["flight_type_preferences"] = []
        if not any("direct" in str(item).lower() for item in merged["flight_type_preferences"]):
            merged["flight_type_preferences"].append(f"{phrasing_func('direct flights only')}")
    
    if current_prefs.get("avoidRedEye"):
        if "red_eye_preferences" not in merged:
            merged["red_eye_preferences"] = []
        if not any("red eye" in str(item).lower() or "evening" in str(item).lower() for item in merged["red_eye_preferences"]):
            merged["red_eye_preferences"].append(f"{phrasing_func('avoiding red-eye flights')}")
    
    if current_prefs.get("cabinClass"):
        if "cabin_class_preferences" not in merged:
            merged["cabin_class_preferences"] = []
        # Clear old cabin class preferences
        cabin = current_prefs['cabinClass']
        merged["cabin_class_preferences"] = [f"{phrasing_func(f'{cabin} cabin class')}"]
    
    if current_prefs.get("preferredTime"):
        if "time_preferences" not in merged:
            merged["time_preferences"] = []
        # Clear old time preferences  
        time = current_prefs['preferredTime']
        merged["time_preferences"] = [f"{phrasing_func(f'{time} departures')}"]
    
    if current_prefs.get("tripType"):
        if "trip_type_preferences" not in merged:
            merged["trip_type_preferences"] = []
        trip = current_prefs['tripType']
        merged["trip_type_preferences"] = [f"{phrasing_func(f'{trip} trips')}"]
    
    return merged

def process_message(user_message: str, user_id: str = "default-user", conversation_history: list = None, current_preferences: dict = None, username: str = None) -> dict:
    """
    Process a user message and generate a response.
    
    Args:
        user_message: The user's message
        user_id: The user identifier
        conversation_history: Previous messages in the conversation
        current_preferences: Current UI preferences (directFlightsOnly, cabinClass, etc.)
        username: The user's username for personalized greetings
        
    Returns:
        dict with 'content' (str) and optionally 'flight_results' (list)
    """
    if conversation_history is None:
        conversation_history = []
    if current_preferences is None:
        current_preferences = {}
    
    # Special handling for preference queries
    message_lower = user_message.lower()
    if any(word in message_lower for word in ["what are my preferences", "show my preferences", "what preferences do i have", "list my preferences", "my preferences"]):
        pref_summary = memory_manager.summarize_preferences(user_id, include_ids=True)
        print(f"[AGENT] Preference query detected. Summary: {pref_summary}")
        
        # Merge current UI preferences with stored preferences
        # Current preferences take priority (they're the latest selections)
        merged_prefs = _merge_preferences(pref_summary, current_preferences)
        
        if not merged_prefs and not current_preferences:
            return {
                "content": "Sorry, you currently do not have any stored preferences. You may have deleted your preferences, or you haven't set any yet. I'd be happy to help you set up your travel preferences such as cabin class, flight type, preferred departure times, and more!",
                "extracted_preferences": [],
                "flight_results": []
            }
        
        # Format preferences for display
        pref_lines = []
        
        category_display = {
            "seat": "🪑 Seat Preferences",
            "airline": "✈️ Preferred Airlines",
            "departure_time": "🕐 Time Preferences",
            "flight_type": "🛫 Flight Type",
            "cabin_class": "🎫 Cabin Class",
            "red_eye": "🌙 Red-Eye Preferences",
            "passenger": "👥 Passenger Type",
            "baggage": "🎒 Baggage",
            "routes": "🗺️ Favorite Routes",
            "budget": "💰 Budget",
            "trip_type": "✈️ Trip Type",
            "location": "📍 Home Location",
            "other": "📋 Other"
        }
        
        has_any_preferences = False
        for category, items in merged_prefs.items():
            if items:
                # First, process and clean items
                valid_items = []
                for item in items:
                    if isinstance(item, dict):
                        item_text = item.get("text", item.get("memory", str(item)))
                    else:
                        item_text = str(item)
                    
                    # Clean up preference text
                    item_text = (item_text
                        .replace("User's travel preference type is ", "")
                        .replace("User ", "")
                        .replace("Prefers", "")
                        .replace("prefers", "")
                        .strip())
                    
                    # Skip very generic terms and "general"
                    if item_text.lower() in ["seat", "airline", "preference", "type", "general"]:
                        continue
                    
                    # Capitalize first letter if needed
                    if item_text and item_text[0].islower():
                        item_text = item_text[0].upper() + item_text[1:]
                    
                    if item_text:  # Only add if not empty after cleaning
                        valid_items.append(item_text)
                
                # Only add category header if there are valid items
                if valid_items:
                    has_any_preferences = True
                    if not pref_lines:  # Add header only if we have preferences
                        pref_lines.append("Here are your currently stored travel preferences:\n")
                    display_name = category_display.get(category, category.replace("_", " ").title())
                    pref_lines.append(f"\n{display_name}:")
                    for item_text in valid_items:
                        pref_lines.append(f"  • {item_text}")
        
        if has_any_preferences:
            pref_lines.append("\n\nFeel free to update these preferences anytime!")
        
        
        return {
            "content": "\n".join(pref_lines),
            "extracted_preferences": [],
            "flight_results": []
        }
    
    system_prompt = get_system_prompt_with_memory(user_id)
    
    # Extract last flight search context if user is expressing new preferences
    extracted_prefs = extract_preferences_from_message(user_message)
    if extracted_prefs and conversation_history:
        # Look for previous flight search in conversation history
        last_search_context = None
        for msg in reversed(conversation_history[-10:]):
            content = msg.get("content", "").lower()
            # Look for mentions of airports/routes
            if any(word in content for word in ["houston", "kathmandu", "hyderabad", "new york", "iath", "ktm", "hyd", "jfk"]):
                if any(word in content for word in ["search", "find", "flight", "from", "to"]):
                    last_search_context = msg.get("content", "")
                    break
        
        if last_search_context:
            system_prompt += "\n\nRECENT SEARCH CONTEXT:\n"
            system_prompt += f"The user recently searched for: {last_search_context}\n"
            system_prompt += "Since they've expressed a NEW PREFERENCE, you MUST re-search using the same route/dates but with their updated preference."
    
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add greeting with username if this is the first message in a new conversation
    greeting_prefix = ""
    if username and len(conversation_history) == 0:
        greetings = [
            f"Hey {username}! 👋 I'm excited to help you find the perfect flights!",
            f"Welcome, {username}! Ready to start your travel adventure?",
            f"Hi {username}! Let's find some amazing flights for you.",
            f"Great to see you, {username}! How can I help with your travel plans?",
        ]
        import random
        greeting_prefix = random.choice(greetings) + "\n\n"
    
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
        applied_prefs_summary = None
        
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
                    # Get preference summary for this search
                    overrides = get_preference_overrides(user_id)
                    applied_prefs_summary = overrides.get("applied_prefs_summary")
                
                if tool_name == "remember_preference":
                    # Use the confirmation message from the tool
                    memory_context = result.get("confirmation", f"Noted: {result.get('preference', '')}")
            
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
            
            # Add greeting if this is the first message
            if greeting_prefix:
                final_content = greeting_prefix + final_content
            
            # Extract preferences from user message and store them individually
            extracted_preferences = extract_preferences_from_message(user_message)
            print(f"[AGENT] Extracted preferences from message: {extracted_preferences}")
            
            if extracted_preferences:
                for pref_label in extracted_preferences:
                    # Map labels to preference types and store individually
                    print(f"[AGENT] Storing preference: {pref_label}")
                    result = memory_manager.store_preference(user_id, "general", pref_label)
                    print(f"[AGENT] Preference storage result: {result}")
                    if "error" in result:
                        print(f"[AGENT ERROR] Failed to store preference '{pref_label}': {result['error']}")
            
            # Also do the general memory extraction
            memory_manager.extract_and_store_preferences(user_id, user_message, final_content)
            
            preferences = memory_manager.get_preferences_summary(user_id)
            if preferences:
                memory_context = "Using your preferences"
            
            return {
                "content": final_content,
                "flight_results": flight_results,
                "memory_context": memory_context,
                "applied_prefs_summary": applied_prefs_summary,
                "extracted_preferences": extracted_preferences
            }
        
        content = assistant_message.content or "I'm sorry, I couldn't generate a response."
        
        memory_manager.extract_and_store_preferences(user_id, user_message, content)
        
        # Extract preferences from user message and return them to be displayed
        extracted_preferences = extract_preferences_from_message(user_message)
        
        return {
            "content": content,
            "flight_results": [],
            "memory_context": None,
            "extracted_preferences": extracted_preferences
        }
        
    except Exception as e:
        return {
            "content": f"I apologize, but I encountered an error while processing your request: {str(e)}. Please try again.",
            "flight_results": [],
            "memory_context": None,
            "extracted_preferences": []
        }
