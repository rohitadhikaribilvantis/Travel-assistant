import { Clock, Plane, ArrowRight, ExternalLink } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { FlightOffer } from "@shared/schema";
import { useAuth } from "@/hooks/use-auth";

interface FlightCardProps {
  flight: FlightOffer;
  index: number;
  onBooking?: () => void;
}

function formatDuration(duration: string): string {
  const match = duration.match(/PT(\d+H)?(\d+M)?/);
  if (!match) return duration;
  const hours = match[1] ? parseInt(match[1]) : 0;
  const minutes = match[2] ? parseInt(match[2]) : 0;
  if (hours && minutes) return `${hours}h ${minutes}m`;
  if (hours) return `${hours}h`;
  return `${minutes}m`;
}

function formatTime(dateTimeString: string): string {
  const date = new Date(dateTimeString);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatDate(dateTimeString: string): string {
  const date = new Date(dateTimeString);
  return date.toLocaleDateString([], { month: "short", day: "numeric" });
}

export function FlightCard({ flight, index, onBooking }: FlightCardProps) {
  const { token } = useAuth();
  const outbound = flight.itineraries[0];
  const returnFlight = flight.itineraries[1];
  const firstSegment = outbound.segments[0];
  const lastSegment = outbound.segments[outbound.segments.length - 1];
  const stops = outbound.segments.length - 1;

  const buildBookingUrl = (website: string): string => {
    const carrier = firstSegment.carrierCode;
    
    // Airline-specific booking homepage URLs (simple and reliable)
    const airlineUrls: Record<string, string> = {
      "UA": "https://www.united.com",
      "AA": "https://www.aa.com",
      "DL": "https://www.delta.com",
      "SW": "https://www.southwest.com",
      "B6": "https://www.jetblue.com",
      "AS": "https://www.alaskaair.com",
      "NK": "https://www.spirit.com",
      "F9": "https://www.frontier.com",
      "AC": "https://www.aircanada.com",
      "BA": "https://www.britishairways.com",
      "LH": "https://www.lufthansa.com",
      "AF": "https://www.airfrance.com",
      "KL": "https://www.klm.com",
      "IB": "https://www.iberia.com",
      "EK": "https://www.emirates.com",
      "QF": "https://www.qantas.com",
      "SQ": "https://www.singaporeair.com",
      "NH": "https://www.ana.co.jp/en",
      "JL": "https://www.jal.co.jp/en",
    };
    
    // Return airline-specific URL if available
    return airlineUrls[carrier] || `https://www.${carrier.toLowerCase()}.com`;
  };

  // Get airline name for button text
  const getAirlineDisplay = (): { name: string; code: string } => {
    return {
      code: firstSegment.carrierCode,
      name: firstSegment.carrierName || firstSegment.carrierCode
    };
  };

  // Ensure the "Book" button does not save preferences and only updates travel history.
  const handleBookClick = async () => {
    console.log("[BOOKING] Book clicked for flight:", firstSegment.carrierCode);

    const hasReturn = !!returnFlight;
    const returnFirstSegment = hasReturn ? returnFlight.segments[0] : undefined;
    const returnLastSegment = hasReturn ? returnFlight.segments[returnFlight.segments.length - 1] : undefined;

    // Record booking
    if (token) {
      try {
        console.log("[BOOKING] Sending POST to record-booking endpoint");
        const response = await fetch("http://localhost:8000/api/memory/record-booking", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({
            origin: firstSegment.departure.iataCode,
            destination: lastSegment.arrival.iataCode,
            airline: firstSegment.carrierCode,
            airline_name: firstSegment.carrierName || firstSegment.carrierCode,
            departure_date: firstSegment.departure.at.split("T")[0],
            departure_time: formatTime(firstSegment.departure.at),
            arrival_time: formatTime(lastSegment.arrival.at),
            trip_type: hasReturn ? "Round Trip" : "One Way",
            return_origin: returnFirstSegment?.departure.iataCode,
            return_destination: returnLastSegment?.arrival.iataCode,
            return_date: returnFirstSegment?.departure.at.split("T")[0],
            return_departure_time: returnFirstSegment ? formatTime(returnFirstSegment.departure.at) : undefined,
            return_arrival_time: returnLastSegment ? formatTime(returnLastSegment.arrival.at) : undefined,
            cabin_class: flight.travelClass?.replace("_", " ") || "economy",
            price: parseFloat(flight.price.total),
            currency: flight.price.currency
          })
        });
        console.log("[BOOKING] Record-booking response:", response.status, await response.json());
      } catch (error) {
        console.error("[BOOKING] Failed to record booking:", error);
      }
    } else {
      console.log("[BOOKING] No token available");
    }

    // Notify parent to refresh
    console.log("[BOOKING] Calling onBooking callback");
    if (onBooking) {
      onBooking();
    } else {
      console.log("[BOOKING] No onBooking callback provided");
    }

    // Open booking
    window.open(buildBookingUrl("airline"), "_blank");
  };

  const airlineDisplay = getAirlineDisplay();

  return (
    <Card
      className="w-full transition-all duration-200 hover-elevate"
      data-testid={`flight-card-${flight.id}`}
    >
      <CardContent className="p-4 md:p-6">
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="flex flex-1 flex-col gap-4">
              <div className="flex items-center gap-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
                  <Plane className="h-5 w-5 text-muted-foreground" />
                </div>
                <div className="flex flex-col">
                  <span className="text-sm font-medium">
                    {firstSegment.carrierName || firstSegment.carrierCode}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {firstSegment.carrierCode} {firstSegment.number}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="flex flex-col items-center">
                  <span className="text-xl font-semibold">
                    {formatTime(firstSegment.departure.at)}
                  </span>
                  <span className="text-sm font-medium">
                    {firstSegment.departure.iataCode}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {formatDate(firstSegment.departure.at)}
                  </span>
                </div>

                <div className="flex flex-1 flex-col items-center gap-1 px-2">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    <span>{formatDuration(outbound.duration)}</span>
                  </div>
                  <div className="relative flex w-full items-center">
                    <div className="h-px flex-1 bg-border" />
                    <ArrowRight className="mx-1 h-3 w-3 text-muted-foreground" />
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {stops === 0 ? "Direct" : `${stops} stop${stops > 1 ? "s" : ""}`}
                  </span>
                </div>

                <div className="flex flex-col items-center">
                  <span className="text-xl font-semibold">
                    {formatTime(lastSegment.arrival.at)}
                  </span>
                  <span className="text-sm font-medium">
                    {lastSegment.arrival.iataCode}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {formatDate(lastSegment.arrival.at)}
                  </span>
                </div>
              </div>

              {returnFlight && (
                <div className="mt-2 border-t pt-4">
                  <div className="flex items-center gap-3">
                    <div className="flex flex-col items-center">
                      <span className="text-lg font-semibold">
                        {formatTime(returnFlight.segments[0].departure.at)}
                      </span>
                      <span className="text-sm font-medium">
                        {returnFlight.segments[0].departure.iataCode}
                      </span>
                    </div>

                    <div className="flex flex-1 flex-col items-center gap-1 px-2">
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        <span>{formatDuration(returnFlight.duration)}</span>
                      </div>
                      <div className="relative flex w-full items-center">
                        <div className="h-px flex-1 bg-border" />
                        <ArrowRight className="mx-1 h-3 w-3 text-muted-foreground" />
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {returnFlight.segments.length - 1 === 0
                          ? "Direct"
                          : `${returnFlight.segments.length - 1} stop${
                              returnFlight.segments.length - 1 > 1 ? "s" : ""
                            }`}
                      </span>
                    </div>

                    <div className="flex flex-col items-center">
                      <span className="text-lg font-semibold">
                        {formatTime(
                          returnFlight.segments[returnFlight.segments.length - 1]
                            .arrival.at
                        )}
                      </span>
                      <span className="text-sm font-medium">
                        {returnFlight.segments[returnFlight.segments.length - 1]
                          .arrival.iataCode}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="flex flex-col items-end gap-2 border-t pt-4 md:border-l md:border-t-0 md:pl-6 md:pt-0">
              <div className="flex flex-col items-end">
                <span className="text-2xl font-bold">
                  {flight.price.currency} {parseFloat(flight.price.total).toFixed(0)}
                </span>
                <span className="text-xs text-muted-foreground">per person</span>
              </div>
              {flight.travelClass && (
                <Badge variant="secondary" size="sm">
                  {flight.travelClass.replace("_", " ")}
                </Badge>
              )}
              <div className="mt-2 flex w-full flex-col gap-2 md:w-auto">
                <Button
                  size="sm"
                  onClick={handleBookClick}
                  className="flex items-center gap-1"
                >
                  Book with {getAirlineDisplay().name}
                  <ExternalLink className="h-3 w-3" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
