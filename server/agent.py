import os
import json
import re
from datetime import datetime, timedelta
from typing import Optional
from openai import OpenAI
from amadeus_client import amadeus_client
from memory_manager import memory_manager
from database import DatabaseStorage
from collections import Counter

db_storage = DatabaseStorage()


_iata_display_cache: dict[str, str] = {}
_iata_country_cache: dict[str, str] = {}


def _iata_display(code: str) -> str:
    if not isinstance(code, str):
        return str(code)
    c = code.strip().upper()
    if len(c) != 3:
        return c

    cached = _iata_display_cache.get(c)
    if cached:
        return cached

    resolved = amadeus_client.resolve_airport_display(c)
    # Cache only if it actually resolved to something more than the code.
    if isinstance(resolved, str) and resolved.strip() and resolved.strip().upper() != c:
        _iata_display_cache[c] = resolved
    return resolved


def _iata_country(code: str) -> str | None:
    if not isinstance(code, str):
        return None
    c = code.strip().upper()
    if len(c) != 3:
        return None

    cached = _iata_country_cache.get(c)
    if cached:
        return cached

    country = amadeus_client.resolve_airport_country(c)
    if isinstance(country, str) and country.strip():
        _iata_country_cache[c] = country.strip()
        return _iata_country_cache[c]
    return None


def _compute_most_travelled_countries(user_id: str, limit: int = 3) -> list[dict]:
    """Compute most traveled destination countries from travel history.

    Prefers DB bookings; falls back to parsing mem0 travel history.
    """

    def norm_iata(value: str | None) -> str | None:
        if not isinstance(value, str):
            return None
        v = value.strip().upper()
        return v if len(v) == 3 else None

    counter: Counter[str] = Counter()

    # 1) DB bookings (deterministic)
    try:
        bookings = db_storage.list_bookings(user_id)
        for b in bookings:
            dest = norm_iata(b.get("destination"))
            if dest:
                country = _iata_country(dest)
                if country:
                    counter[country] += 1
    except Exception as e:
        print(f"[AGENT] Failed to load bookings for countries: {e}")

    # 2) Fallback: mem0 travel history
    if not counter:
        try:
            memories = memory_manager.get_travel_history(user_id) or []

            def add_destination_iata(dest_code: str | None):
                d = norm_iata(dest_code)
                if not d:
                    return
                country = _iata_country(d)
                if country:
                    counter[country] += 1

            for m in memories:
                if not m:
                    continue

                memory_text = ""
                if isinstance(m, dict):
                    meta = m.get("metadata") or {}
                    add_destination_iata(meta.get("destination"))
                    memory_text = (m.get("memory") or "").strip()
                else:
                    memory_text = str(m).strip()

                if not memory_text:
                    continue

                # Pattern: "IAH → KTM" or "IAH->KTM" (destination is second code)
                arrow = re.findall(r"\b([A-Z]{3})\b\s*(?:→|->)\s*\b([A-Z]{3})\b", memory_text)
                for _o, d in arrow:
                    add_destination_iata(d)

                # Pattern: "from IAH to KTM"
                from_to = re.findall(r"from\s+([A-Z]{3})\s+to\s+([A-Z]{3})", memory_text, flags=re.IGNORECASE)
                for _o, d in from_to:
                    add_destination_iata(d)

        except Exception as e:
            print(f"[AGENT] Failed to compute countries from memories: {e}")

    if not counter:
        return []

    ranked = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
    out: list[dict] = []
    for country, count in ranked[: max(1, limit)]:
        out.append({"country": country, "count": count})
    return out


def _compute_frequent_routes(user_id: str, limit: int = 5) -> list[dict]:
    """Compute frequent routes from travel history.

    Prefers DB bookings (deterministic). If none exist, falls back to mem0-based
    travel history so answers match what the UI currently shows.
    """

    def norm_iata(value: str | None) -> str | None:
        if not isinstance(value, str):
            return None
        code = value.strip().upper()
        return code if len(code) == 3 else None

    counter: Counter[tuple[str, str]] = Counter()

    # 1) DB bookings
    try:
        bookings = db_storage.list_bookings(user_id)
        for b in bookings:
            o = norm_iata(b.get("origin"))
            d = norm_iata(b.get("destination"))
            if o and d:
                counter[(o, d)] += 1

            ro = norm_iata(b.get("return_origin"))
            rd = norm_iata(b.get("return_destination"))
            if ro and rd:
                counter[(ro, rd)] += 1
    except Exception as e:
        print(f"[AGENT] Failed to load bookings for routes: {e}")

    # 2) Fallback: mem0 travel history
    if not counter:
        try:
            memories = memory_manager.get_travel_history(user_id) or []

            def add_route_pair(o: str | None, d: str | None):
                oo = norm_iata(o)
                dd = norm_iata(d)
                if oo and dd:
                    counter[(oo, dd)] += 1

            for m in memories:
                if not m:
                    continue

                if isinstance(m, dict):
                    meta = m.get("metadata") or {}
                    add_route_pair(meta.get("origin"), meta.get("destination"))
                    add_route_pair(meta.get("return_origin"), meta.get("return_destination"))

                    memory_text = (m.get("memory") or "").strip()
                else:
                    memory_text = str(m).strip()

                if not memory_text:
                    continue

                # Pattern: "IAH → KTM" or "IAH->KTM"
                arrow = re.findall(r"\b([A-Z]{3})\b\s*(?:→|->)\s*\b([A-Z]{3})\b", memory_text)
                for o, d in arrow:
                    add_route_pair(o, d)

                # Pattern: "from Houston (IAH) to Kathmandu (KTM)"
                paren = re.findall(r"\(([A-Z]{3})\)\s*.*?\(([A-Z]{3})\)", memory_text)
                for o, d in paren:
                    add_route_pair(o, d)

                # Pattern: "from IAH to KTM"
                from_to = re.findall(r"from\s+([A-Z]{3})\s+to\s+([A-Z]{3})", memory_text, flags=re.IGNORECASE)
                for o, d in from_to:
                    add_route_pair(o, d)

        except Exception as e:
            print(f"[AGENT] Failed to compute frequent routes from memories: {e}")

    if not counter:
        return []

    ranked = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
    out: list[dict] = []
    for (o, d), count in ranked[: max(1, limit)]:
        out.append({
            "route": f"{_iata_display(o)} → {_iata_display(d)}",
            "count": count,
        })
    return out


def _get_travel_history_items(user_id: str, limit: int = 50) -> list[dict]:
    """Return travel history items in the same shape the UI expects.

    Uses DB bookings first (deterministic), and falls back to mem0 travel history.
    """
    def _clean_text(value: object) -> Optional[str]:
        if not isinstance(value, str):
            return None
        v = value.strip()
        if not v:
            return None
        if v.lower() in {"a", "an", "the"}:
            return None
        return v

    try:
        rows = db_storage.list_bookings(user_id)
        if rows:
            cleaned_rows: list[dict] = []
            seen_db: set[tuple] = set()
            for r in rows:
                if not isinstance(r, dict):
                    continue
                cleaned = dict(r)
                for k in [
                    "origin",
                    "destination",
                    "airline",
                    "airline_code",
                    "airline_name",
                    "tripType",
                    "departure_date",
                    "departure_time",
                    "arrival_time",
                    "return_origin",
                    "return_destination",
                    "return_date",
                    "return_departure_time",
                    "return_arrival_time",
                    "cabin_class",
                    "currency",
                ]:
                    if k in cleaned:
                        cleaned[k] = _clean_text(cleaned.get(k))
                db_key = (
                    (cleaned.get("origin") or "").upper(),
                    (cleaned.get("destination") or "").upper(),
                    cleaned.get("departure_date") or "",
                    cleaned.get("return_date") or "",
                    cleaned.get("departure_time") or "",
                    cleaned.get("return_departure_time") or "",
                    cleaned.get("airline_code") or cleaned.get("airline_name") or cleaned.get("airline") or "",
                    cleaned.get("cabin_class") or "",
                    str(cleaned.get("price") or ""),
                    cleaned.get("tripType") or "",
                )
                if any(v for v in db_key) and db_key in seen_db:
                    continue
                if any(v for v in db_key):
                    seen_db.add(db_key)
                cleaned_rows.append(cleaned)
            return cleaned_rows[: max(1, limit)]
    except Exception as e:
        print(f"[AGENT] Failed to load bookings from DB: {e}")

    # Fallback: mem0-based travel history
    memories = memory_manager.get_travel_history(user_id) or []
    items: list[dict] = []
    for m in memories:
        if not m:
            continue

        if isinstance(m, dict):
            memory_str = (m.get("memory") or "").strip()
            meta = m.get("metadata") or {}
        else:
            memory_str = str(m).strip()
            meta = {}

        # Keep only booking-like entries
        lower = memory_str.lower()
        if "searched" in lower:
            continue
        if not (
            "book" in lower
            or "booked" in lower
            or "book with" in lower
            or re.search(r"\b[A-Z]{3}\b\s*(?:→|->)\s*\b[A-Z]{3}\b", memory_str)
        ):
            continue

        item = {
            "origin": _clean_text(meta.get("origin")),
            "destination": _clean_text(meta.get("destination")),
            "airline": _clean_text(meta.get("airline") or meta.get("airline_name") or meta.get("airline_code")),
            "airline_code": _clean_text(meta.get("airline_code") or meta.get("airline")),
            "airline_name": _clean_text(meta.get("airline_name")),
            "tripType": _clean_text(meta.get("tripType") or meta.get("trip_type")),
            "departure_date": _clean_text(meta.get("departure_date")),
            "departure_time": _clean_text(meta.get("departure_time")),
            "arrival_time": _clean_text(meta.get("arrival_time")),
            "return_origin": _clean_text(meta.get("return_origin")),
            "return_destination": _clean_text(meta.get("return_destination")),
            "return_date": _clean_text(meta.get("return_date")),
            "return_departure_time": _clean_text(meta.get("return_departure_time")),
            "return_arrival_time": _clean_text(meta.get("return_arrival_time")),
            "cabin_class": _clean_text(meta.get("cabin_class")),
            "price": meta.get("price"),
            "currency": _clean_text(meta.get("currency")) or "USD",
            "booked_at": _clean_text(meta.get("booked_at")),
            "memory": memory_str,
        }
        items.append(item)

        if len(items) >= max(1, limit):
            break

    # De-duplicate (mem0 can return near-duplicates)
    deduped: list[dict] = []
    seen: set[tuple] = set()
    for it in items:
        memory_key = re.sub(r"\s+", " ", (it.get("memory") or "").strip().lower())
        fields_key = (
            (it.get("origin") or "").upper(),
            (it.get("destination") or "").upper(),
            it.get("departure_date") or "",
            it.get("return_date") or "",
            (it.get("airline_name") or it.get("airline") or ""),
            it.get("cabin_class") or "",
            str(it.get("price") or ""),
            it.get("tripType") or "",
        )
        # If we have any structured signal, dedupe primarily on that; otherwise fallback to memory text.
        key = fields_key if any(v for v in fields_key) else (memory_key,)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(it)
    return deduped


def _recommendations_from_history(user_id: str, *, solo: bool) -> str:
    """Generate lightweight trip recommendations grounded in travel history."""
    routes = _compute_frequent_routes(user_id, limit=5)
    if not routes:
        return (
            "I don't see any prior bookings yet, so I can't personalize recommendations from your travel history. "
            "If you tell me what kind of solo trip you want (food, culture, nature, budget), I'll suggest options."
        )

    # Extract destination codes from route display strings like "Houston (IAH) → Tokyo (NRT)"
    dest_codes: list[str] = []
    dest_names: list[str] = []
    for r in routes:
        route_text = str(r.get("route", ""))
        parts = [p.strip() for p in route_text.split("→")]
        if len(parts) == 2:
            dest_names.append(parts[1])
            m = re.search(r"\(([A-Z]{3})\)\s*$", parts[1])
            if m:
                dest_codes.append(m.group(1))

    top_places = ", ".join(dest_names[:2]) if dest_names else "your recent trips"

    # Very small heuristic mapping (keep it minimal and safe)
    suggestions: list[str] = []
    if any(c in {"NRT", "HND", "KIX"} for c in dest_codes):
        suggestions.extend([
            "Kyoto, Japan — easy to explore solo with temples, cafés, and great transit",
            "Osaka, Japan — food-forward city with lively neighborhoods",
            "Seoul, South Korea — safe, efficient, and great for solo itineraries",
        ])
    if any(c in {"KTM"} for c in dest_codes):
        suggestions.extend([
            "Pokhara, Nepal — relaxed lakeside base and great for day hikes",
            "Paro/Thimphu, Bhutan — culture + mountains (permit-based, but very solo-friendly)",
        ])

    if not suggestions:
        suggestions = [
            "Singapore — very safe, great public transit, easy for solo travelers",
            "Lisbon, Portugal — walkable, friendly, lots of day trips",
            "Reykjavík, Iceland — easy tours and nature with strong solo-travel infrastructure",
        ]

    # Keep response concise; user asked for recommendations, not a history dump.
    lines = [
        (
            f"Based on your travel history (you frequently fly to {top_places}), here are solo-trip ideas:"
            if solo
            else f"Based on your travel history (you frequently fly to {top_places}), here are trip ideas:"
        ),
        "",
    ]
    for s in suggestions[:5]:
        lines.append(f"- {s}")
    lines.append("\nTell me: do you want culture, nature, or food-focused?")
    return "\n".join(lines)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def _infer_preference_memory_type(preference_text: str) -> str | None:
    """Infer a structured preference type from free-form preference text."""
    if not isinstance(preference_text, str):
        return None
    t = preference_text.strip().lower()
    if not t:
        return None

    if "red eye" in t or "red-eye" in t or "redeye" in t:
        return "red_eye"
    if "non-stop" in t or "nonstop" in t or "direct" in t or "layover" in t or "stops" in t:
        return "flight_type"
    if "cabin" in t or "class" in t or any(k in t for k in ["economy", "premium", "business", "first"]):
        return "cabin_class"
    if "morning" in t or "afternoon" in t or "evening" in t or "departure" in t:
        return "departure_time"
    if "window" in t or "aisle" in t or "seat" in t:
        return "seat"
    if "baggage" in t or "luggage" in t or "carry-on" in t or "checked" in t:
        return "baggage"
    if "airline" in t or "carrier" in t:
        return "airline"
    if any(k in t for k in ["traveling alone", "travelling alone", "solo", "with family", "kids", "children", "with partner", "spouse"]):
        return "passenger"
    if "one-way" in t or "one way" in t or "round trip" in t or "round-trip" in t:
        return "trip_type"

    return None

def extract_preferences_from_message(user_message: str) -> list[str]:
    """Extract detailed preference statements from user messages."""
    preferences = []
    message_lower = user_message.lower()

    # Cabin class preferences (important for immediate re-search)
    cabin_patterns: list[tuple[str, str]] = [
        (r"premium\s+economy", "I prefer Premium Economy class flights"),
        (r"\bbusiness\b", "I prefer Business class flights"),
        (r"\bfirst\b", "I prefer First Class flights"),
        # Economy must come after premium economy
        (r"\beconomy\b", "I prefer Economy class flights"),
    ]
    
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
        # Avoidance should win over generic time mentions
        (r"(?:hate|avoid|don\s*'?t\s+like|do\s+not\s+like)\s+(?:flying\s+)?(?:in\s+the\s+)?mornings?\b", "Avoid morning flights"),
        (r"(?:hate|avoid|don\s*'?t\s+like|do\s+not\s+like)\s+(?:flying\s+)?(?:in\s+the\s+)?afternoons?\b", "Avoid afternoon flights"),
        (r"(?:hate|avoid|don\s*'?t\s+like|do\s+not\s+like)\s+(?:flying\s+)?(?:in\s+the\s+)?evenings?\b", "Avoid evening flights"),
        (r"(?:hate|avoid|don\s*'?t\s+like|do\s+not\s+like)\s+(?:early\s+)?morning\s+flights?", "Avoid morning flights"),
        (r"(?:hate|avoid|don\s*'?t\s+like|do\s+not\s+like)\s+afternoon\s+flights?", "Avoid afternoon flights"),
        (r"(?:hate|avoid|don\s*'?t\s+like|do\s+not\s+like)\s+(?:late\s+)?evening\s+flights?", "Avoid evening flights"),

        # Positive preferences (capture common phrasing)
        (r"(?:i\s+)?(?:prefer|like|love|want)\s+(?:to\s+)?(?:fly|flying)\s+(?:in\s+the\s+)?mornings?\b", "morning flights"),
        (r"(?:i\s+)?(?:prefer|like|love|want)\s+(?:to\s+)?(?:fly|flying)\s+(?:in\s+the\s+)?afternoons?\b", "afternoon flights"),
        (r"(?:i\s+)?(?:prefer|like|love|want)\s+(?:to\s+)?(?:fly|flying)\s+(?:in\s+the\s+)?evenings?\b", "evening flights"),
        (r"(?:early\s+)?morning\s+flights?", "morning flights"),
        (r"late\s+evening\s+flights?", "evening flights"),
        (r"afternoon\s+flights?", "afternoon flights"),
        (r"(?:prefer|want)\s+(?:early|late|morning|afternoon|evening)\s+departures?", "preferred departure time"),
        (r"\b(?:in\s+the\s+)?mornings?\b", "morning flights"),
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
    # IMPORTANT: Don't store "cheap" as a long-lived preference.
    # Treat budget as a preference only when the user expresses it as a stable constraint.
    budget_patterns = [
        (
            r"\b(on\s+a\s+budget|tight\s+budget|budget[-\s]?friendly|budget[-\s]?conscious|as\s+cheap\s+as\s+possible|cheapest\s+possible)\b",
            "budget conscious",
        ),
    ]

    # Red-eye preferences
    red_eye_patterns = [
        (r"red\s*-?eye", "Avoid red-eye flights"),
        (r"redeye", "Avoid red-eye flights"),
        (r"(?:hate|avoid|don\s*'?t\s+like|do\s+not\s+like)\s+.*red\s*-?eye", "Avoid red-eye flights"),
    ]
    
    # Location/home preferences
    location_patterns = [
        (r"(?:i\s+)?(?:live|based|from)\s+(?:in\s+)?(\w+)", "home city preference"),
    ]
    
    all_patterns = [
        seat_patterns, airline_patterns, time_patterns, 
        flight_patterns, passenger_patterns, baggage_patterns, budget_patterns, red_eye_patterns,
        cabin_patterns,
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

    # Resolve contradictions: if the user expresses avoidance for a time bucket,
    # don't also store the positive version (which can overwrite the avoid entry
    # for mutually-exclusive DB types).
    avoid_buckets: set[str] = set()
    for pref in unique_prefs:
        pl = pref.lower()
        if pl.startswith("avoid "):
            for b in ("morning", "afternoon", "evening"):
                if b in pl:
                    avoid_buckets.add(b)

    if avoid_buckets:
        filtered: list[str] = []
        for pref in unique_prefs:
            pl = pref.lower()
            # Drop positive time labels that conflict with avoidance.
            if pl in {"morning flights", "afternoon flights", "evening flights"}:
                for b in avoid_buckets:
                    if b in pl:
                        break
                else:
                    filtered.append(pref)
                continue
            # Also drop the generic time label if it's for an avoided bucket.
            if pl == "preferred departure time" and any(b in (user_message or "").lower() for b in avoid_buckets):
                continue
            filtered.append(pref)
        unique_prefs = filtered
    
    return unique_prefs


def _augment_current_preferences_from_message(current_preferences: Optional[dict], user_message: str) -> dict:
    """Best-effort: turn free-form messages like 'economy please' into current prefs.

    This affects the *current* search immediately even if the user didn't open the UI dropdown.
    """
    merged = dict(current_preferences or {})
    if not isinstance(user_message, str):
        return merged

    t = user_message.lower()

    # Cabin class
    if "premium" in t and "economy" in t:
        merged["cabinClass"] = "Premium Economy"
    elif re.search(r"\bfirst\b", t):
        merged["cabinClass"] = "First Class"
    elif re.search(r"\bbusiness\b", t):
        merged["cabinClass"] = "Business"
    elif re.search(r"\beconomy\b", t):
        merged["cabinClass"] = "Economy"

    # Red-eye avoidance
    if re.search(r"red\s*-?eye|redeye", t) and re.search(r"hate|avoid|don't\s+like|do\s+not\s+like|no\s+red", t):
        merged["avoidRedEye"] = True

    # Direct flights
    if re.search(r"\bdirect\b|non\s*-?stop", t) and re.search(r"only|prefer|please|want|need", t):
        merged["directFlightsOnly"] = True

    return merged

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

def get_preference_overrides(user_id: str, current_preferences: Optional[dict] = None) -> dict:
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

        # Build a post-filtering preference payload for the flight results.
        # This is used by amadeus_client._filter_flights_by_preferences.
        user_preferences: dict = {}

        # Apply current UI preferences first (highest priority)
        if current_preferences:
            cabin = current_preferences.get("cabinClass")
            if isinstance(cabin, str) and cabin.strip():
                cabin_l = cabin.strip().lower()
                if "first" in cabin_l:
                    overrides["travel_class"] = "FIRST"
                    applied_prefs.append("First Class (current selection)")
                elif "business" in cabin_l:
                    overrides["travel_class"] = "BUSINESS"
                    applied_prefs.append("Business Class (current selection)")
                elif "premium" in cabin_l:
                    overrides["travel_class"] = "PREMIUM_ECONOMY"
                    applied_prefs.append("Premium Economy (current selection)")
                elif "economy" in cabin_l:
                    overrides["travel_class"] = "ECONOMY"
                    applied_prefs.append("Economy (current selection)")

            if current_preferences.get("directFlightsOnly") is True:
                overrides["non_stop"] = True
                applied_prefs.append("direct/non-stop (current selection)")

            if current_preferences.get("avoidRedEye") is True:
                user_preferences["avoid_red_eye"] = True
                applied_prefs.append("avoid red-eye flights (current selection)")
        
        # Check for passenger preferences
        passenger_items = (prefs.get("seat_preferences") or prefs.get("passenger") or prefs.get("passenger_preferences") or [])
        if passenger_items:
            seat_text = " ".join([str(item) for item in passenger_items]).lower()
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
        # (Only apply if current UI selection didn't already set it)
        cabin_items = (prefs.get("cabin_class_preferences") or prefs.get("cabin_class") or [])
        if not overrides.get("travel_class") and cabin_items:
            cabin_text = " ".join([str(item) for item in cabin_items]).lower()
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
        elif not overrides.get("travel_class"):
            print(f"[PREFS DEBUG] No cabin class preferences stored for user {user_id}")
        
        # Check for direct flight preferences (only if UI didn't already set it)
        flight_items = (prefs.get("flight_type_preferences") or prefs.get("flight_type") or [])
        if overrides.get("non_stop") is None and flight_items:
            flight_text = " ".join([str(item) for item in flight_items]).lower()
            print(f"[PREFS DEBUG] Flight type preferences found: {flight_text}")
            if "direct" in flight_text or "non-stop" in flight_text:
                overrides["non_stop"] = True
                applied_prefs.append("direct/non-stop preference")

        # Check for red-eye avoidance (only if UI didn't already set it)
        if user_preferences.get("avoid_red_eye") is not True:
            red_eye_items = (prefs.get("red_eye_preferences") or prefs.get("red_eye") or [])
            red_eye_text = " ".join([str(item) for item in red_eye_items]).lower()
            if red_eye_text and ("red" in red_eye_text and "eye" in red_eye_text):
                user_preferences["avoid_red_eye"] = True
                applied_prefs.append("avoid red-eye flights preference")
        
        # Check for time/departure preferences
        if prefs.get("time_preferences") or prefs.get("departure_time"):
            time_prefs = prefs.get("time_preferences", []) or prefs.get("departure_time", [])
            time_text = " ".join([str(item) for item in time_prefs]).lower()
            print(f"[PREFS DEBUG] Time preferences found: {time_text}")
            if time_text:
                overrides["time_preference"] = time_text
                user_preferences["departure_time_preferences"] = [time_text]
                # Avoidance semantics (e.g. "avoid afternoon")
                if "avoid" in time_text or "hate" in time_text or "don't like" in time_text or "do not like" in time_text:
                    if "morning" in time_text:
                        applied_prefs.append("avoid morning flights")
                    elif "afternoon" in time_text:
                        applied_prefs.append("avoid afternoon flights")
                    elif "evening" in time_text:
                        applied_prefs.append("avoid evening flights")
                    else:
                        applied_prefs.append(f"avoid time preference: {time_text}")
                elif "morning" in time_text:
                    applied_prefs.append("morning flights")
                elif "afternoon" in time_text:
                    applied_prefs.append("afternoon flights")
                elif "evening" in time_text:
                    applied_prefs.append("evening flights")
                else:
                    applied_prefs.append(f"time preference: {time_text}")
        
        overrides["applied_prefs_summary"] = " & ".join(applied_prefs) if applied_prefs else None
        overrides["user_preferences"] = user_preferences
        print(f"[PREFS] Extracted overrides for user {user_id}: {overrides}")
        return overrides
    except Exception as e:
        print(f"[PREFS ERROR] Error extracting preference overrides: {e}")
        import traceback
        traceback.print_exc()
        return {}
        return {}

def execute_tool(tool_name: str, arguments: dict, user_id: str, current_preferences: Optional[dict] = None) -> dict:
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
        
        # Apply preference overrides (UI selection should win)
        overrides = get_preference_overrides(user_id, current_preferences)
        adults = overrides.get("adults", adults)
        travel_class = overrides.get("travel_class", travel_class)
        non_stop = overrides.get("non_stop", non_stop)
        user_preferences = overrides.get("user_preferences") or {}
        
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
                non_stop=non_stop,
                user_preferences=user_preferences,
            )
            
            print(f"[FLIGHT SEARCH] Result: {result}")
            
            if result.get("error"):
                print(f"[FLIGHT SEARCH] Error: {result['error']}")
                return {"error": result["error"], "flights": []}
            
            flights = result.get("data", [])
            tagged_flights = amadeus_client.tag_flight_offers(flights)
            
            print(f"[FLIGHT SEARCH] Found {len(tagged_flights)} flights")
            return {
                "flights": tagged_flights,
                "count": len(tagged_flights),
                "applied_preferences": overrides.get("applied_prefs_summary"),
            }
        except Exception as e:
            print(f"[FLIGHT SEARCH] Exception: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": str(e), "flights": []}
    
    elif tool_name == "remember_preference":
        preference = arguments.get("preference", "")
        print(f"[PREF] Storing preference: {preference}")
        
        pref_type = _infer_preference_memory_type(preference)
        # Store the preference directly. Avoid forcing memory_type="general" since
        # the memory layer intentionally filters "general" entries from the UI.
        result = memory_manager.add_structured_memory(
            user_id=user_id,
            category="preference",
            content=preference,
            memory_type=pref_type,
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

    # Convert free-form messages like "economy please" into effective current preferences
    # so the next search uses the updated cabin class immediately.
    current_preferences = _augment_current_preferences_from_message(current_preferences, user_message)
    if current_preferences is None:
        current_preferences = {}
    
    # Special handling for preference queries
    message_lower = user_message.lower()

    def _looks_like_explicit_flight_search(text: str) -> bool:
        t = (text or "").lower()
        if not t.strip():
            return False

        # Strong intent verbs.
        if re.search(r"\b(find|search|show|book|get|look\s*up|pull\s*up)\b", t):
            return True

        # Route pattern.
        if re.search(r"\bfrom\b.+\bto\b", t):
            return True

        return False

    # Preference-only update guard:
    # Users often message things like "I hate afternoon flights" intending only to update preferences.
    # Do NOT automatically re-run the last route/search unless they explicitly asked to search.
    extracted_prefs_only = extract_preferences_from_message(user_message)
    if extracted_prefs_only and not _looks_like_explicit_flight_search(user_message):
        # Keep response concise; don't trigger any flight tools.
        # (The API layer persists extracted_preferences to DB/mem0.)
        confirmations = []
        for p in extracted_prefs_only:
            if isinstance(p, str) and p.strip():
                confirmations.append(p.strip())
        confirmation_text = ", ".join(confirmations[:3]) if confirmations else "your preferences"
        return {
            "content": f"Got it — I’ll remember: {confirmation_text}.",
            "extracted_preferences": extracted_prefs_only,
            "flight_results": [],
        }

    # Special handling for most traveled country queries
    if any(
        phrase in message_lower
        for phrase in [
            "most travelled country",
            "most traveled country",
            "most travelled countries",
            "most traveled countries",
            "most visited country",
            "where do i travel most",
            "what is my most traveled country",
            "what is my most travelled country",
        ]
    ):
        countries = _compute_most_travelled_countries(user_id, limit=3)
        if not countries:
            return {
                "content": "I don't have any booking history yet, so I can't determine your most frequent destination country. Book a flight and then ask again.",
                "flight_results": None,
            }

        top = countries[0]
        lines = [
            f"Based on your booking history (planned trips), your most frequent destination country is {top['country']} ({top['count']} trip(s))."
        ]

        if len(countries) > 1:
            lines.append("")
            lines.append("Top destination countries:")
            for item in countries[:3]:
                lines.append(f"- {item['country']}: {item['count']} trip(s)")

        return {"content": "\n".join(lines), "flight_results": None}

    # Special handling for frequent routes queries (based on travel history)
    if any(
        phrase in message_lower
        for phrase in [
            "routes do i travel frequently",
            "what routes do i travel frequently",
            "my frequent routes",
            "frequent routes",
            "most frequent routes",
            "routes i travel",
            "where do i travel frequently",
        ]
    ):
        routes = _compute_frequent_routes(user_id, limit=5)
        if not routes:
            return {
                "content": "You don't have any bookings yet, so I can't determine frequent routes. Book a flight and then ask again.",
                "extracted_preferences": [],
                "flight_results": [],
            }

        lines = ["Here are your most frequent routes (from your travel history):\n"]
        for i, r in enumerate(routes, start=1):
            count = r.get("count", 0)
            trip_word = "trip" if count == 1 else "trips"
            lines.append(f"{i}. {r.get('route')} — {count} {trip_word}")

        return {
            "content": "\n".join(lines),
            "extracted_preferences": [],
            "flight_results": [],
        }

    if any(word in message_lower for word in ["what are my preferences", "show my preferences", "what preferences do i have", "list my preferences", "my preferences"]):
        pref_summary = memory_manager.summarize_preferences(user_id, include_ids=True)
        print(f"[AGENT] Preference query detected. Summary: {pref_summary}")
        
        # Merge current UI preferences with stored preferences
        # Current preferences take priority (they're the latest selections)
        merged_prefs = _merge_preferences(pref_summary, current_preferences)

        # Add frequent routes derived from travel history
        try:
            frequent_routes = _compute_frequent_routes(user_id, limit=5)
            if frequent_routes:
                merged_prefs["routes"] = [
                    f"{r['route']} ({r['count']})" for r in frequent_routes if r.get("route")
                ]
        except Exception as e:
            print(f"[AGENT] Failed to compute frequent routes: {e}")
        
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
    
    # Special handling for recommendations based on travel history
    recommendation_triggers = [
        "recommend",
        "suggest",
        "recommendation",
        "ideas",
        "where should i go",
        "where to go",
        "itinerary",
        "plan a trip",
    ]
    history_context_triggers = [
        "based on my travel history",
        "based on my bookings",
        "based on travel history",
        "my travel history",
        "travel history",
        "my bookings",
    ]

    if any(t in message_lower for t in recommendation_triggers) and any(
        t in message_lower for t in history_context_triggers
    ):
        print(f"[AGENT] Travel-history-based recommendation query detected for user {user_id}")
        return {
            "content": _recommendations_from_history(user_id, solo=("solo" in message_lower)),
            "extracted_preferences": [],
            "flight_results": [],
        }

    # Special handling for travel history queries
    if any(
        word in message_lower
        for word in [
            "show my travel history",
            "list my travel history",
            "show travel history",
            "show my bookings",
            "my bookings",
            "where have i traveled",
            "where have i been",
            "travel history",
        ]
    ) and not any(t in message_lower for t in recommendation_triggers):
        print(f"[AGENT] Travel history query detected for user {user_id}")
        travel_history_items = _get_travel_history_items(user_id, limit=50)
        print(f"[AGENT] Returning {len(travel_history_items) if travel_history_items else 0} travel history items")

        if not travel_history_items:
            return {
                "content": "You haven't booked any flights yet. When you book a flight, it will appear in your travel history!",
                "extracted_preferences": [],
                "flight_results": [],
                "travel_history": []
            }

        # Keep the assistant text minimal; the UI will render cards.
        history_lines = ["Here's your travel bookings:"]

        return {
            "content": "\n".join(history_lines),
            "extracted_preferences": [],
            "flight_results": [],
            "travel_history": travel_history_items
        }
    
    system_prompt = get_system_prompt_with_memory(user_id)
    
    # Extract last flight search context if user is expressing new preferences.
    # Provide this as optional context only; do NOT force an automatic re-search.
    extracted_prefs = extracted_prefs_only
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
            system_prompt += "If the user asks to re-run the search, reuse the same route/dates and apply the new preference."
    
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
                
                result = execute_tool(tool_name, arguments, user_id, current_preferences)
                tool_results.append({
                    "tool_call_id": tool_call.id,
                    "output": json.dumps(result)
                })
                
                if tool_name == "search_flights" and result.get("flights"):
                    flight_results = result["flights"]
                    # Get preference summary for this search
                    overrides = get_preference_overrides(user_id, current_preferences)
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
            
            # Extract preferences from user message (persistence handled by API layer)
            extracted_preferences = extract_preferences_from_message(user_message)
            print(f"[AGENT] Extracted preferences from message: {extracted_preferences}")
            
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
