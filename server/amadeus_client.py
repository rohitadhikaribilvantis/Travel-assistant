import os
import requests
from datetime import datetime
from typing import Optional

class AmadeusClient:
    """Client for interacting with Amadeus Flight API."""
    
    BASE_URL = "https://test.api.amadeus.com"
    
    def __init__(self):
        self.api_key = os.environ.get("AMADEUS_API_KEY")
        self.api_secret = os.environ.get("AMADEUS_API_SECRET")
        self.access_token = None
        self.token_expires_at = None
        
    def _get_access_token(self) -> str:
        """Get or refresh the access token."""
        if self.access_token and self.token_expires_at:
            if datetime.now().timestamp() < self.token_expires_at - 60:
                return self.access_token
        
        url = f"{self.BASE_URL}/v1/security/oauth2/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.api_secret
        }
        
        response = requests.post(url, data=data)
        
        if response.status_code != 200:
            raise Exception(f"Failed to get access token: {response.text}")
        
        token_data = response.json()
        self.access_token = token_data["access_token"]
        self.token_expires_at = datetime.now().timestamp() + token_data["expires_in"]
        
        return self.access_token
    
    def _get_headers(self) -> dict:
        """Get authorization headers."""
        token = self._get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        travel_class: Optional[str] = None,
        non_stop: bool = False,
        max_results: int = 10,
        max_price: Optional[int] = None,
        user_preferences: Optional[dict] = None
    ) -> dict:
        """
        Search for flight offers.
        
        Args:
            origin: Origin airport IATA code (e.g., 'JFK')
            destination: Destination airport IATA code (e.g., 'LAX')
            departure_date: Departure date in YYYY-MM-DD format
            return_date: Return date in YYYY-MM-DD format (optional, for round trip)
            adults: Number of adult passengers
            children: Number of children
            infants: Number of infants
            travel_class: ECONOMY, PREMIUM_ECONOMY, BUSINESS, or FIRST
            non_stop: If True, only search for direct flights
            max_results: Maximum number of results to return
            max_price: Maximum price filter
            user_preferences: Dictionary of user preferences for filtering (e.g., {'preferred_cabin': 'BUSINESS'})
        """
        url = f"{self.BASE_URL}/v2/shopping/flight-offers"
        
        # Apply user preferences if provided
        if user_preferences:
            # If user prefers non-stop flights, apply that filter
            if user_preferences.get("non_stop_only", False):
                non_stop = True
            # If user has a cabin class preference and none was explicitly requested, use it
            if not travel_class and user_preferences.get("preferred_cabin"):
                travel_class = user_preferences.get("preferred_cabin")
            # If user has a max price preference
            if not max_price and user_preferences.get("max_price"):
                max_price = user_preferences.get("max_price")
        params = {
            "originLocationCode": origin.upper(),
            "destinationLocationCode": destination.upper(),
            "departureDate": departure_date,
            "adults": adults,
            "max": max_results,
            "currencyCode": "USD"
        }
        
        if return_date:
            params["returnDate"] = return_date
        if children > 0:
            params["children"] = children
        if infants > 0:
            params["infants"] = infants
        if travel_class:
            params["travelClass"] = travel_class
        if non_stop:
            params["nonStop"] = True
        if max_price:
            params["maxPrice"] = max_price
            
        try:
            print(f"[AMADEUS] Fetching token...")
            headers = self._get_headers()
            print(f"[AMADEUS] Token obtained, sending request to {url}")
            print(f"[AMADEUS] Params: {params}")
            
            response = requests.get(url, headers=headers, params=params)
            
            print(f"[AMADEUS] Response status: {response.status_code}")
            print(f"[AMADEUS] Response: {response.text}")
            
            if response.status_code != 200:
                error_msg = response.json().get("errors", [{}])[0].get("detail", response.text)
                print(f"[AMADEUS] Error: {error_msg}")
                return {"error": error_msg, "data": []}
            
            data = response.json()
            processed = self._process_flight_offers(data)
            
            # Apply post-search filtering based on user preferences
            if user_preferences:
                processed["data"] = self._filter_flights_by_preferences(processed.get("data", []), user_preferences)
            
            return processed
            
        except Exception as e:
            return {"error": str(e), "data": []}
    
    def _process_flight_offers(self, raw_data: dict) -> dict:
        """Process and enrich flight offers data."""
        offers = raw_data.get("data", [])
        dictionaries = raw_data.get("dictionaries", {})
        carriers = dictionaries.get("carriers", {})
        
        processed_offers = []
        
        for offer in offers:
            processed = {
                "id": offer["id"],
                "price": {
                    "total": offer["price"]["total"],
                    "currency": offer["price"]["currency"],
                    "base": offer["price"].get("base", offer["price"]["total"])
                },
                "numberOfBookableSeats": offer.get("numberOfBookableSeats"),
                "validatingAirlineCodes": offer.get("validatingAirlineCodes", []),
                "itineraries": []
            }
            
            for itinerary in offer["itineraries"]:
                processed_itinerary = {
                    "duration": itinerary["duration"],
                    "segments": []
                }
                
                for segment in itinerary["segments"]:
                    carrier_code = segment["carrierCode"]
                    processed_segment = {
                        "departure": {
                            "iataCode": segment["departure"]["iataCode"],
                            "terminal": segment["departure"].get("terminal"),
                            "at": segment["departure"]["at"]
                        },
                        "arrival": {
                            "iataCode": segment["arrival"]["iataCode"],
                            "terminal": segment["arrival"].get("terminal"),
                            "at": segment["arrival"]["at"]
                        },
                        "carrierCode": carrier_code,
                        "carrierName": carriers.get(carrier_code, carrier_code),
                        "number": segment["number"],
                        "aircraft": segment.get("aircraft", {}).get("code"),
                        "duration": segment["duration"],
                        "numberOfStops": segment.get("numberOfStops", 0)
                    }
                    processed_itinerary["segments"].append(processed_segment)
                
                processed["itineraries"].append(processed_itinerary)
            
            traveler_pricings = offer.get("travelerPricings", [])
            if traveler_pricings:
                cabin = traveler_pricings[0].get("fareDetailsBySegment", [{}])[0].get("cabin")
                if cabin:
                    processed["travelClass"] = cabin
            
            processed_offers.append(processed)
        
        return {"data": processed_offers, "meta": raw_data.get("meta", {})}
    
    def _filter_flights_by_preferences(self, flights: list, user_preferences: dict) -> list:
        """
        Filter flights based on user preferences.
        
        Args:
            flights: List of flight offers
            user_preferences: Dictionary with preference filters
            
        Returns:
            Filtered list of flights
        """
        filtered = flights
        
        # Filter by avoided airlines
        avoided_airlines = user_preferences.get("avoided_airlines", [])
        if avoided_airlines:
            filtered = [f for f in filtered if not any(
                segment.get("carrierCode") in avoided_airlines 
                for itinerary in f.get("itineraries", []) 
                for segment in itinerary.get("segments", [])
            )]
        
        # Filter by preferred airlines (if specified)
        preferred_airlines = user_preferences.get("preferred_airlines", [])
        if preferred_airlines:
            filtered = [f for f in filtered if any(
                segment.get("carrierCode") in preferred_airlines 
                for itinerary in f.get("itineraries", []) 
                for segment in itinerary.get("segments", [])
            )]
        
        # Filter by max stops
        max_stops = user_preferences.get("max_stops")
        if max_stops is not None:
            filtered = [f for f in filtered if all(
                len(itinerary.get("segments", [])) - 1 <= max_stops
                for itinerary in f.get("itineraries", [])
            )]
        
        # Filter by departure time preferences
        departure_times = user_preferences.get("departure_time_preferences", [])
        if departure_times:
            filtered = [f for f in filtered if self._matches_departure_preferences(f, departure_times)]
        
        # Filter by red-eye avoidance
        if user_preferences.get("avoid_red_eye", False):
            filtered = [f for f in filtered if not self._is_red_eye(f)]
        
        return filtered
    
    def _matches_departure_preferences(self, flight: dict, time_preferences: list) -> bool:
        """Check if flight matches departure time preferences (early morning, afternoon, evening)."""
        try:
            itinerary = flight.get("itineraries", [{}])[0]
            segments = itinerary.get("segments", [])
            if not segments:
                return True
            
            departure_time_str = segments[0].get("departure", {}).get("at", "")
            if not departure_time_str:
                return True
            
            # Extract hour from ISO datetime
            hour = int(departure_time_str.split("T")[1].split(":")[0])
            
            for pref in time_preferences:
                pref_lower = pref.lower()
                if "morning" in pref_lower and 5 <= hour < 12:
                    return True
                if "afternoon" in pref_lower and 12 <= hour < 17:
                    return True
                if "evening" in pref_lower and 17 <= hour < 23:
                    return True
            
            return False
        except:
            return True
    
    def _is_red_eye(self, flight: dict) -> bool:
        """Check if flight is a red-eye (late night departure 10pm-6am)."""
        try:
            itinerary = flight.get("itineraries", [{}])[0]
            segments = itinerary.get("segments", [])
            if not segments:
                return False
            
            departure_time_str = segments[0].get("departure", {}).get("at", "")
            if not departure_time_str:
                return False
            
            hour = int(departure_time_str.split("T")[1].split(":")[0])
            return hour >= 22 or hour < 6
        except:
            return False
    
    def tag_flight_offers(self, offers: list) -> list:
        """Add comparison tags to flight offers (cheapest, fastest, best)."""
        if not offers:
            return offers
        
        prices = [(i, float(o["price"]["total"])) for i, o in enumerate(offers)]
        durations = []
        
        for i, offer in enumerate(offers):
            total_mins = 0
            for itin in offer["itineraries"]:
                duration = itin["duration"]
                import re
                match = re.match(r'PT(\d+H)?(\d+M)?', duration)
                if match:
                    hours = int(match.group(1)[:-1]) if match.group(1) else 0
                    mins = int(match.group(2)[:-1]) if match.group(2) else 0
                    total_mins += hours * 60 + mins
            durations.append((i, total_mins))
        
        for offer in offers:
            offer["tags"] = []
        
        if prices:
            cheapest_idx = min(prices, key=lambda x: x[1])[0]
            offers[cheapest_idx]["tags"].append("cheapest")
        
        if durations:
            fastest_idx = min(durations, key=lambda x: x[1])[0]
            offers[fastest_idx]["tags"].append("fastest")
        
        if prices and durations:
            price_min = min(p[1] for p in prices)
            price_max = max(p[1] for p in prices) or price_min + 1
            dur_min = min(d[1] for d in durations)
            dur_max = max(d[1] for d in durations) or dur_min + 1
            
            best_score = float('inf')
            best_idx = 0
            
            for i, offer in enumerate(offers):
                price = float(offer["price"]["total"])
                dur = next(d[1] for d in durations if d[0] == i)
                
                price_norm = (price - price_min) / (price_max - price_min) if price_max != price_min else 0
                dur_norm = (dur - dur_min) / (dur_max - dur_min) if dur_max != dur_min else 0
                
                score = 0.6 * price_norm + 0.4 * dur_norm
                
                if score < best_score:
                    best_score = score
                    best_idx = i
            
            if "cheapest" not in offers[best_idx]["tags"] and "fastest" not in offers[best_idx]["tags"]:
                offers[best_idx]["tags"].append("best")
        
        return offers


amadeus_client = AmadeusClient()
