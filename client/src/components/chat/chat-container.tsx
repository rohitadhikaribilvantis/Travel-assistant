import { useEffect, useRef, useState } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageBubble } from "./message-bubble";
import { EmptyState } from "./empty-state";
import { LoadingSkeleton } from "./loading-skeleton";
import { FlightFilter } from "./flight-filter";
import { JourneySummary } from "./journey-summary";
import { useAuth } from "@/hooks/use-auth";
import type { ChatMessage, FlightOffer } from "@shared/schema";

interface ChatContainerProps {
  messages: ChatMessage[];
  isLoading?: boolean;
}

export function ChatContainer({ messages, isLoading }: ChatContainerProps) {
  const { user } = useAuth();
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [showFilter, setShowFilter] = useState(false);
  const [filteredFlights, setFilteredFlights] = useState<FlightOffer[] | null>(null);
  const [currentFlights, setCurrentFlights] = useState<FlightOffer[] | null>(null);

  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isLoading]);

  // Extract journey details from messages
  const extractJourneyInfo = () => {
    const lastFlightMessage = messages.findLast((m) => m.flightResults?.length);
    return {
      origin: extractFromMessages(/from|depart|leave|origin.*?([A-Z]{3})/i),
      destination: extractFromMessages(/to|arrive|destination.*?([A-Z]{3})/i),
      departureDate: extractFromMessages(/(?:on|depart|leave).*?(\d{4}-\d{2}-\d{2}|\w+ \d{1,2})/i),
      passengers: extractFromMessages(/(\d+)\s*(?:passenger|person|traveler|pax)/i),
      cabinClass: extractFromMessages(/(economy|business|first|premium)/i),
    };
  };

  const extractFromMessages = (pattern: RegExp): string | undefined => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const match = messages[i].content.match(pattern);
      if (match) return match[1];
    }
    return undefined;
  };

  // Get last flight results message
  const lastFlightMessage = messages.findLast((m) => m.flightResults?.length);
  const hasFlights = lastFlightMessage && lastFlightMessage.flightResults.length > 0;

  if (messages.length === 0 && !isLoading) {
    return <EmptyState />;
  }

  return (
    <div className="flex flex-1 gap-4 overflow-hidden">
      <ScrollArea className="flex-1" ref={scrollRef}>
        <div className="mx-auto max-w-4xl py-4 px-4">
          {/* Journey Summary */}
          {hasFlights && <JourneySummary summary={extractJourneyInfo()} />}

          {/* Messages */}
          {messages.map((message) => (
            <MessageBubble 
              key={message.id} 
              message={{
                ...message,
                flightResults: showFilter && filteredFlights && currentFlights === message.flightResults
                  ? filteredFlights
                  : message.flightResults
              }}
              userAvatar={user?.avatar}
              onShowFilter={() => {
                setCurrentFlights(message.flightResults || null);
                setShowFilter(true);
                setFilteredFlights(null);
              }}
            />
          ))}
          {isLoading && <LoadingSkeleton />}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      {/* Flight Filter Panel */}
      {showFilter && currentFlights && currentFlights.length > 0 && (
        <div className="hidden lg:block w-80 border-l">
          <FlightFilter
            flights={currentFlights}
            onFilter={setFilteredFlights}
            onClose={() => {
              setShowFilter(false);
              setFilteredFlights(null);
            }}
          />
        </div>
      )}
    </div>
  );
}
