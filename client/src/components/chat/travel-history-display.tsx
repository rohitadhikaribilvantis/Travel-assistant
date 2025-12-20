import { Plane, Calendar, DollarSign, MapPin, Clock, Users, RotateCcw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface Booking {
  origin?: string;
  destination?: string;
  airline?: string;
  airline_code?: string;
  airline_name?: string;
  departure_date?: string;
  departure_time?: string;
  arrival_time?: string;
  return_origin?: string;
  return_destination?: string;
  return_date?: string;
  return_departure_time?: string;
  return_arrival_time?: string;
  cabin_class?: string;
  price?: number;
  currency?: string;
  booked_at?: string;
  passenger?: string;
  passengerCount?: number;
  tripType?: string;
  memory?: string;
}

interface TravelHistoryDisplayProps {
  bookings: Booking[];
}

// Airline code to name mapping
const AIRLINE_NAMES: Record<string, string> = {
  "AA": "American Airlines",
  "AC": "Air Canada",
  "AF": "Air France",
  "BA": "British Airways",
  "CM": "Copa Airlines",
  "DL": "Delta",
  "EK": "Emirates",
  "FI": "Icelandair",
  "FR": "Frontier",
  "G3": "GOL",
  "KL": "KLM",
  "LA": "LATAM",
  "LH": "Lufthansa",
  "NK": "Spirit",
  "QF": "Qantas",
  "QR": "Qatar Airways",
  "SK": "SAS",
  "SQ": "Singapore Airlines",
  "SY": "Sun Country",
  "SW": "Southwest",
  "TK": "Turkish Airlines",
  "UA": "United",
  "VB": "VivaAerobus",
  "VX": "Virgin America",
  "WN": "Southwest",
};

function getAirlineName(code: string): string {
  return AIRLINE_NAMES[code] || code;
}

export function TravelHistoryDisplay({ bookings }: TravelHistoryDisplayProps) {
  if (!bookings || bookings.length === 0) {
    return (
      <Card className="bg-muted/30">
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground text-center">
            No bookings yet. Start searching for flights!
          </p>
        </CardContent>
      </Card>
    );
  }

  // Parse booking data from memory string or structured data
  const parseBooking = (booking: Booking): Booking => {
    // We merge: explicit/structured fields win, but we still parse `memory`
    // to fill missing details (airline name, time window, return leg, etc.).
    const base: Booking = {
      ...booking,
      origin: booking.origin || "",
      destination: booking.destination || "",
      departure_date: booking.departure_date || "",
      airline:
        booking.airline_name || booking.airline || booking.airline_code || "",
    };

    // Helper: parse as much as possible from memory text.
    const parseFromMemory = (memoryStr: string): Partial<Booking> => {
      const normalizedMemory = memoryStr.replace(/^\s*Travel History:\s*/i, "").trim();
      
      // Try multiple patterns for different memory formats
      // Pattern 1: "United UA NYC → LHR on 2024-01-15 • Economy • USD 450"
      let routeMatch = normalizedMemory.match(/(\w{3})\s*→\s*(\w{3})/);

      // Pattern 1b: "... from Houston (IAH) to Kathmandu (KTM) ..."
      if (!routeMatch) {
        routeMatch = normalizedMemory.match(/from\s+.*?\(([A-Z]{3})\).*?to\s+.*?\(([A-Z]{3})\)/i);
      }
      
      // Pattern 2: "User booked a flight from IAH to SIN with AC on 20..."
      if (!routeMatch) {
        routeMatch = normalizedMemory.match(/from\s+(\w{3})\s+to\s+(\w{3})/i);
      }
      
      // Pattern 3: "booked a flight from IAH to SIN"
      if (!routeMatch) {
        routeMatch = normalizedMemory.match(/flight from (\w{3}) (?:to|and) (\w{3})/i);
      }
      
      // Extract airline code - try multiple patterns
      let airlineCode = normalizedMemory.match(/with\s+(\w{2})\s/i)?.[1]; // "with AC"
      if (!airlineCode) {
        // Only match a 2-letter carrier code when it's adjacent to a route marker,
        // to avoid accidentally capturing "AM"/"PM" from times.
        airlineCode = normalizedMemory.match(/\b([A-Z]{2})\s+[A-Z]{3}\s*(?:→|to)\s*[A-Z]{3}\b/)?.[1];
      }
      if (airlineCode && (airlineCode === "AM" || airlineCode === "PM")) {
        airlineCode = undefined;
      }

      // Extract airline name when no code is present
      // Examples we store:
      // - "Booked flight: UNITED AIRLINES IAH → NRT on 2025-12-21 (10:25 AM - 03:30 PM) ..."
      // - "User traveled on United Airlines from IAH to NRT on 2025-12-21, departing at ..."
      let airlineName: string | undefined;
      const bookedPrefixMatch = normalizedMemory.match(/^(?:Booked\s+flight:\s*)?(.+?)\s+([A-Z]{3})\s*→\s*[A-Z]{3}/);
      if (bookedPrefixMatch) {
        airlineName = bookedPrefixMatch[1]?.trim();
      }
      if (!airlineName) {
        const traveledMatch = normalizedMemory.match(/\bon\s+(.+?)\s+from\s+[A-Z]{3}\s+to\s+[A-Z]{3}\b/i);
        if (traveledMatch) {
          airlineName = traveledMatch[1]?.trim();
        }
      }

      // Additional formats:
      // - "User booked a United Airlines flight from Houston (IAH) to Kathmandu (KTM) ..."
      // - "United Airlines flight from IAH to KTM ..."
      if (!airlineName) {
        const bookedAirlineMatch = normalizedMemory.match(/\bbooked\s+(?:an?\s+)?(.+?)\s+flight\b/i);
        if (bookedAirlineMatch) {
          airlineName = bookedAirlineMatch[1]?.trim();
        }
      }
      if (!airlineName) {
        const leadingAirlineMatch = normalizedMemory.match(/^(.+?)\s+flight\s+from\s+/i);
        if (leadingAirlineMatch) {
          airlineName = leadingAirlineMatch[1]?.trim();
        }
      }

      // Extract time window like "(10:25 AM - 03:30 PM)"
      let departureTime: string | undefined;
      let arrivalTime: string | undefined;
      const timeWindowMatch = normalizedMemory.match(/\(([^)]+)\)/);
      if (timeWindowMatch) {
        const parts = timeWindowMatch[1].split(/\s*-\s*/).map(s => s.trim()).filter(Boolean);
        if (parts.length >= 2) {
          departureTime = parts[0];
          arrivalTime = parts[1];
        }
      }

      // Alternate time format: "... on 2025-12-22 from 05:00 AM to 04:00 PM ..."
      if (!departureTime || !arrivalTime) {
        const fromToMatch = normalizedMemory.match(/\bfrom\s+(\d{1,2}:\d{2}\s+[AP]M)\s+to\s+(\d{1,2}:\d{2}\s+[AP]M)\b/i);
        if (fromToMatch) {
          departureTime = departureTime || fromToMatch[1];
          arrivalTime = arrivalTime || fromToMatch[2];
        }
      }

      // Extract return leg (if present) from the stored string format
      // Example: "| Return NRT → IAH on 2025-12-28 (04:55 PM - 09:10 AM)"
      let returnOrigin: string | undefined;
      let returnDestination: string | undefined;
      let returnDate: string | undefined;
      let returnDepartureTime: string | undefined;
      let returnArrivalTime: string | undefined;
      const returnMatch = normalizedMemory.match(/\|\s*Return\s+([A-Z]{3})\s*→\s*([A-Z]{3})(?:\s+on\s+(\d{4}-\d{2}-\d{2}))?(?:\s*\(([^)]+)\))?/i);
      if (returnMatch) {
        returnOrigin = returnMatch[1];
        returnDestination = returnMatch[2];
        returnDate = returnMatch[3];
        if (returnMatch[4]) {
          const parts = returnMatch[4].split(/\s*-\s*/).map(s => s.trim()).filter(Boolean);
          if (parts.length >= 2) {
            returnDepartureTime = parts[0];
            returnArrivalTime = parts[1];
          }
        }
      }
      
      const dateMatch = normalizedMemory.match(/on\s+(\d{2}\/\d{2}\/\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2})/);
      const cabinMatch =
        normalizedMemory.match(/•\s+(Economy|Business|First|Premium(?:\s+Economy)?)/i) ||
        normalizedMemory.match(/\bin\s+(Economy|Business|First|Premium(?:\s+Economy)?)\s+class\b/i) ||
        normalizedMemory.match(/cabin[:\s]+(\w+)/i);
      const priceMatch = normalizedMemory.match(/USD\s+(\d+)|(\d+)\s*USD/i) || normalizedMemory.match(/\$\s*(\d+)/);
      
      // Extract passenger count - try multiple patterns
      let passengerCount = booking.passengerCount;
      if (!passengerCount) {
        // Pattern 1: "2 passengers" or "1 passenger"
        let countMatch = normalizedMemory.match(/(\d+)\s+passenger/i);
        if (countMatch) passengerCount = parseInt(countMatch[1]);
        
        // Pattern 2: "for 2" or "booked 3 tickets"
        if (!countMatch) {
          countMatch = normalizedMemory.match(/(?:for|tickets?[:\s])(\d+)/i);
          if (countMatch) passengerCount = parseInt(countMatch[1]);
        }
      }
      
      // Extract trip type - round trip or one way
      let tripType = booking.tripType;
      if (!tripType) {
        if (/round.?trip|return/i.test(normalizedMemory)) {
          tripType = "Round Trip";
        } else if (/one.?way|one way|single|outbound/i.test(normalizedMemory)) {
          tripType = "One Way";
        }
      }

      // Default: if we didn't detect a return leg, treat as one-way.
      if (!tripType && !/\|\s*Return\b/i.test(normalizedMemory)) {
        tripType = "One Way";
      }
      
      // Extract passenger name - try multiple patterns
      let passengerName = booking.passenger;
      if (!passengerName) {
        // Pattern 1: "for John Doe" or "passenger John Doe"
        let pMatch = normalizedMemory.match(/(?:for|passenger[:\s]+)([A-Za-z\s]+?)(?:,|\.|on\s+date)/i);
        if (pMatch) passengerName = pMatch[1].trim();
        
        // Pattern 2: Look for name pattern at start: "John Doe booked"
        if (!passengerName) {
          pMatch = normalizedMemory.match(/^([A-Z][a-z]+\s+[A-Z][a-z]+)\s+booked/);
          if (pMatch) passengerName = pMatch[1];
        }
      }
      
      // Try to extract date in various formats
      let finalDate = dateMatch?.[1] || booking.departure_date;
      if (finalDate && finalDate.includes("/")) {
        // Convert MM/DD/YYYY to YYYY-MM-DD for consistency
        const [month, day, year] = finalDate.split("/");
        finalDate = `${year}-${month}-${day}`;
      }

      return {
        airline: airlineCode ? getAirlineName(airlineCode) : (airlineName || ""),
        origin: routeMatch?.[1] || "",
        destination: routeMatch?.[2] || "",
        departure_date: finalDate || "",
        departure_time: departureTime,
        arrival_time: arrivalTime,
        return_origin: returnOrigin,
        return_destination: returnDestination,
        return_date: returnDate,
        return_departure_time: returnDepartureTime,
        return_arrival_time: returnArrivalTime,
        cabin_class: cabinMatch?.[1] || cabinMatch?.[2] || "",
        price: priceMatch ? parseInt(priceMatch[1] || priceMatch[2]) : undefined,
        passenger: passengerName,
        passengerCount,
        tripType,
      };
    };

    const parsedFromMemory = base.memory ? parseFromMemory(base.memory) : {};

    const merged: Booking = {
      ...base,
      // Fill gaps from memory parsing
      origin: base.origin || parsedFromMemory.origin || "",
      destination: base.destination || parsedFromMemory.destination || "",
      airline: base.airline || parsedFromMemory.airline || "",
      departure_date: base.departure_date || parsedFromMemory.departure_date || "",
      departure_time: base.departure_time || parsedFromMemory.departure_time,
      arrival_time: base.arrival_time || parsedFromMemory.arrival_time,
      return_origin: base.return_origin || parsedFromMemory.return_origin,
      return_destination: base.return_destination || parsedFromMemory.return_destination,
      return_date: base.return_date || parsedFromMemory.return_date,
      return_departure_time: base.return_departure_time || parsedFromMemory.return_departure_time,
      return_arrival_time: base.return_arrival_time || parsedFromMemory.return_arrival_time,
      cabin_class: base.cabin_class || parsedFromMemory.cabin_class,
      tripType: base.tripType || parsedFromMemory.tripType,
      price: base.price ?? parsedFromMemory.price,
      passenger: base.passenger || parsedFromMemory.passenger,
      passengerCount: base.passengerCount || parsedFromMemory.passengerCount,
    };

    // Normalize airline display: if we ended up with a carrier code, map to name.
    if (merged.airline && merged.airline.length === 2 && /^[A-Z]{2}$/.test(merged.airline)) {
      merged.airline = getAirlineName(merged.airline);
    }

    return merged;
  };

  return (
    <div className="space-y-3 w-full">
      <div className="space-y-3">
        {bookings.map((booking, idx) => {
          const parsed = parseBooking(booking);
          
          // Filter out non-booking items (like "searched route")
          const memoryLower = parsed.memory?.toLowerCase() || "";
          if (memoryLower.includes("searched") || (!parsed.origin && memoryLower.includes("route"))) {
            return null;
          }

          const hasRoute = !!(parsed.origin && parsed.destination);
          const displayTripType = parsed.tripType || (parsed.return_date ? "Round Trip" : "One Way");

          return (
            <Card key={idx} className="overflow-hidden hover:shadow-lg transition-all duration-200 border-l-4 border-l-blue-500 bg-gradient-to-br from-slate-50 to-white dark:from-slate-900 dark:to-slate-800">
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    <div className="bg-blue-100 dark:bg-blue-900 p-2 rounded-lg flex-shrink-0 mt-1">
                      <Plane className="w-4 h-4 text-blue-600 dark:text-blue-300" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <CardTitle className="text-base font-bold text-slate-900 dark:text-white mb-1">
                        {hasRoute ? (
                          <>
                            {parsed.origin} <span className="text-blue-500 mx-1">→</span> {parsed.destination}
                          </>
                        ) : (
                          <span className="truncate">Travel Booking</span>
                        )}
                      </CardTitle>
                      {parsed.airline && <p className="text-xs font-medium text-blue-600 dark:text-blue-400">{parsed.airline}</p>}
                      {parsed.departure_time && parsed.arrival_time && (
                        <p className="text-xs text-muted-foreground">
                          {parsed.departure_time} - {parsed.arrival_time}
                        </p>
                      )}
                    </div>
                  </div>
                  {parsed.cabin_class && (
                    <Badge className="whitespace-nowrap flex-shrink-0 bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200 border-0">
                      {parsed.cabin_class}
                    </Badge>
                  )}
                </div>
              </CardHeader>
              <CardContent className="pt-2">
                <div className="grid grid-cols-2 gap-3">
                  {(parsed.departure_date || parsed.departure_time) && (
                    <div className="flex items-start gap-2 p-2 bg-slate-100 dark:bg-slate-700 rounded-lg col-span-2">
                      <Calendar className="w-4 h-4 text-slate-600 dark:text-slate-300 flex-shrink-0 mt-0.5" />
                      <div className="min-w-0">
                        <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">{displayTripType}</p>
                        <p className="text-xs font-semibold text-slate-900 dark:text-white truncate">
                          Depart: {parsed.departure_date ? new Date(parsed.departure_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : ""}
                          {parsed.departure_time ? ` • ${parsed.departure_time}` : ""}
                        </p>
                        {(parsed.return_date || parsed.return_departure_time) && (
                          <p className="text-xs font-semibold text-slate-900 dark:text-white truncate">
                            Return: {parsed.return_date ? new Date(parsed.return_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : ""}
                            {parsed.return_departure_time ? ` • ${parsed.return_departure_time}` : ""}
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                  {parsed.price && (
                    <div className="flex items-start gap-2 p-2 bg-green-50 dark:bg-green-900/20 rounded-lg">
                      <DollarSign className="w-4 h-4 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
                      <div className="min-w-0">
                        <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">Price</p>
                        <p className="text-xs font-semibold text-green-700 dark:text-green-400">
                          {parsed.currency || 'USD'} {parsed.price.toLocaleString()}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        }).filter(Boolean)}
      </div>
    </div>
  );
}
