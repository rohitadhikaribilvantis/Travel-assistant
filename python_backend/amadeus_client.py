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
        max_price: Optional[int] = None
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
        """
        url = f"{self.BASE_URL}/v2/shopping/flight-offers"
        
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
            params["nonStop"] = "true"
        if max_price:
            params["maxPrice"] = max_price
            
        try:
            response = requests.get(url, headers=self._get_headers(), params=params)
            
            if response.status_code != 200:
                error_msg = response.json().get("errors", [{}])[0].get("detail", response.text)
                return {"error": error_msg, "data": []}
            
            data = response.json()
            return self._process_flight_offers(data)
            
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
