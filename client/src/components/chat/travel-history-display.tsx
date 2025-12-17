import { Plane, Calendar, DollarSign, MapPin, Clock, Users, RotateCcw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface Booking {
  origin?: string;
  destination?: string;
  airline?: string;
  departure_date?: string;
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
    // Prefer metadata values over parsing memory string
    if (booking.origin && booking.destination) {
      return {
        ...booking,
        airline: booking.airline ? getAirlineName(booking.airline) : booking.airline,
        origin: booking.origin,
        destination: booking.destination,
        departure_date: booking.departure_date || "",
        cabin_class: booking.cabin_class || "",
        price: booking.price,
      };
    }
    
    if (booking.memory && !booking.origin) {
      const memoryStr = booking.memory;
      
      // Try multiple patterns for different memory formats
      // Pattern 1: "United UA NYC → LHR on 2024-01-15 • Economy • USD 450"
      let routeMatch = memoryStr.match(/(\w{3})\s*→\s*(\w{3})/);
      
      // Pattern 2: "User booked a flight from IAH to SIN with AC on 20..."
      if (!routeMatch) {
        routeMatch = memoryStr.match(/from\s+(\w{3})\s+to\s+(\w{3})/i);
      }
      
      // Pattern 3: "booked a flight from IAH to SIN"
      if (!routeMatch) {
        routeMatch = memoryStr.match(/flight from (\w{3}) (?:to|and) (\w{3})/i);
      }
      
      // Extract airline code - try multiple patterns
      let airlineCode = memoryStr.match(/with\s+(\w{2})\s/i)?.[1]; // "with AC"
      if (!airlineCode) {
        airlineCode = memoryStr.match(/\b([A-Z]{2})\s/)?.[1];
      }
      
      const dateMatch = memoryStr.match(/on\s+(\d{2}\/\d{2}\/\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2})/);
      const cabinMatch = memoryStr.match(/•\s+(Economy|Business|First|Premium)|cabin[:\s]+(\w+)/i);
      const priceMatch = memoryStr.match(/USD\s+(\d+)|(\d+)\s*USD/i) || memoryStr.match(/\$\s*(\d+)/);
      
      // Extract passenger count - try multiple patterns
      let passengerCount = booking.passengerCount;
      if (!passengerCount) {
        // Pattern 1: "2 passengers" or "1 passenger"
        let countMatch = memoryStr.match(/(\d+)\s+passenger/i);
        if (countMatch) passengerCount = parseInt(countMatch[1]);
        
        // Pattern 2: "for 2" or "booked 3 tickets"
        if (!countMatch) {
          countMatch = memoryStr.match(/(?:for|tickets?[:\s])(\d+)/i);
          if (countMatch) passengerCount = parseInt(countMatch[1]);
        }
      }
      
      // Extract trip type - round trip or one way
      let tripType = booking.tripType;
      if (!tripType) {
        if (/round.?trip|return/i.test(memoryStr)) {
          tripType = "Round Trip";
        } else if (/one.?way|one way|single|outbound/i.test(memoryStr)) {
          tripType = "One Way";
        }
      }
      
      // Extract passenger name - try multiple patterns
      let passengerName = booking.passenger;
      if (!passengerName) {
        // Pattern 1: "for John Doe" or "passenger John Doe"
        let pMatch = memoryStr.match(/(?:for|passenger[:\s]+)([A-Za-z\s]+?)(?:,|\.|on\s+date)/i);
        if (pMatch) passengerName = pMatch[1].trim();
        
        // Pattern 2: Look for name pattern at start: "John Doe booked"
        if (!passengerName) {
          pMatch = memoryStr.match(/^([A-Z][a-z]+\s+[A-Z][a-z]+)\s+booked/);
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
        ...booking,
        airline: airlineCode ? getAirlineName(airlineCode) : (booking.airline || ""),
        origin: routeMatch?.[1] || booking.origin || "",
        destination: routeMatch?.[2] || booking.destination || "",
        departure_date: finalDate || booking.departure_date || "",
        cabin_class: cabinMatch?.[1] || cabinMatch?.[2] || booking.cabin_class || "",
        price: priceMatch ? parseInt(priceMatch[1] || priceMatch[2]) : booking.price,
        passenger: passengerName || booking.passenger,
        passengerCount: passengerCount || booking.passengerCount,
        tripType: tripType || booking.tripType,
        memory: memoryStr
      };
    }
    return booking;
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
          
          // Skip if we couldn't parse any meaningful data
          if (!parsed.origin || !parsed.destination) {
            return null;
          }

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
                        {parsed.origin} <span className="text-blue-500 mx-1">→</span> {parsed.destination}
                      </CardTitle>
                      {parsed.airline && <p className="text-xs font-medium text-blue-600 dark:text-blue-400">{parsed.airline}</p>}
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
                  {parsed.departure_date && (
                    <div className="flex items-start gap-2 p-2 bg-slate-100 dark:bg-slate-700 rounded-lg">
                      <Calendar className="w-4 h-4 text-slate-600 dark:text-slate-300 flex-shrink-0 mt-0.5" />
                      <div className="min-w-0">
                        <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">Departure</p>
                        <p className="text-xs font-semibold text-slate-900 dark:text-white truncate">
                          {new Date(parsed.departure_date).toLocaleDateString('en-US', { 
                            month: 'short', 
                            day: 'numeric',
                            year: 'numeric'
                          })}
                        </p>
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
                  {parsed.passengerCount && (
                    <div className="flex items-start gap-2 p-2 bg-cyan-50 dark:bg-cyan-900/20 rounded-lg">
                      <Users className="w-4 h-4 text-cyan-600 dark:text-cyan-400 flex-shrink-0 mt-0.5" />
                      <div className="min-w-0">
                        <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">Passengers</p>
                        <p className="text-xs font-semibold text-cyan-700 dark:text-cyan-400">
                          {parsed.passengerCount} {parsed.passengerCount === 1 ? 'person' : 'people'}
                        </p>
                      </div>
                    </div>
                  )}
                  {parsed.tripType && (
                    <div className="flex items-start gap-2 p-2 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
                      <RotateCcw className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                      <div className="min-w-0">
                        <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">Trip Type</p>
                        <p className="text-xs font-semibold text-amber-700 dark:text-amber-400">
                          {parsed.tripType}
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
