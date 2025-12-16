import { Clock, Plane, ArrowRight, ExternalLink } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { FlightOffer } from "@shared/schema";

interface FlightCardProps {
  flight: FlightOffer;
  index: number;
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

export function FlightCard({ flight, index }: FlightCardProps) {
  const outbound = flight.itineraries[0];
  const returnFlight = flight.itineraries[1];
  const firstSegment = outbound.segments[0];
  const lastSegment = outbound.segments[outbound.segments.length - 1];
  const stops = outbound.segments.length - 1;

  const getTagVariant = (tag: string) => {
    switch (tag) {
      case "cheapest":
        return "default";
      case "fastest":
        return "secondary";
      case "best":
        return "outline";
      default:
        return "secondary";
    }
  };

  const getTagLabel = (tag: string) => {
    switch (tag) {
      case "cheapest":
        return "Cheapest";
      case "fastest":
        return "Fastest";
      case "best":
        return "Best Value";
      default:
        return tag;
    }
  };

  const buildBookingUrl = (website: string): string => {
    const origin = firstSegment.departure.iataCode;
    const destination = lastSegment.arrival.iataCode;
    const departDate = firstSegment.departure.at.split("T")[0];
    const departTime = firstSegment.departure.at.split("T")[1]?.substring(0, 5);
    const arrivalTime = lastSegment.arrival.at.split("T")[1]?.substring(0, 5);
    const carrier = firstSegment.carrierCode;
    const flightNumber = firstSegment.number;

    const baseUrls = {
      google: `https://www.google.com/flights/search?tfs=${origin}${destination}${departDate.replace(/-/g, "")}r`,
      skyscanner: `https://www.skyscanner.com/transport/flights/${origin}/${destination}/${departDate}?adultsv2=1&cabinclass=${flight.travelClass?.toLowerCase() || "economy"}`,
      kayak: `https://www.kayak.com/flights/${origin}-${destination}/${departDate}?a=${carrier}`,
      expedia: `https://www.expedia.com/Flights-Search?trip=oneway&leg1=from:${origin},to:${destination},departure:${departDate}&passengers=1&cabin=${flight.travelClass?.toLowerCase() || "economy"}`,
    };
    return baseUrls[website as keyof typeof baseUrls] || baseUrls.google;
  };

  const websites = [
    { name: "Google Flights", key: "google" },
  ];

  return (
    <Card
      className="w-full transition-all duration-200 hover-elevate"
      data-testid={`flight-card-${flight.id}`}
    >
      <CardContent className="p-4 md:p-6">
        <div className="flex flex-col gap-4">
          {flight.tags && flight.tags.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {flight.tags.map((tag) => (
                <Badge key={tag} variant={getTagVariant(tag)} size="sm">
                  {getTagLabel(tag)}
                </Badge>
              ))}
            </div>
          )}

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
                  onClick={() => window.open(buildBookingUrl("google"), "_blank")}
                  className="flex items-center gap-1"
                >
                  Book on Google Flights
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
