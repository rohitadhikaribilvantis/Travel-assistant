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
  isLoadingConversation?: boolean;
  onBooking?: () => void;
}

export function ChatContainer({ messages, isLoading, isLoadingConversation, onBooking }: ChatContainerProps) {
  const { user } = useAuth();
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [showFilter, setShowFilter] = useState(false);
  const [filteredFlights, setFilteredFlights] = useState<FlightOffer[] | null>(null);
  const [currentFlights, setCurrentFlights] = useState<FlightOffer[] | null>(null);

  useEffect(() => {
    // When a conversation is being loaded (typically after refresh), do not auto-scroll
    // to the bottom. Users expect to read the conversation from the top.
    if (isLoadingConversation) {
      const root = scrollRef.current;
      const viewport = root?.querySelector<HTMLElement>("[data-radix-scroll-area-viewport]");
      if (viewport) viewport.scrollTop = 0;
      return;
    }

    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isLoading, isLoadingConversation]);

  // Extract journey details from messages
  const extractJourneyInfo = () => {
    const lastFlightMessage = messages.findLast((m) => m.flightResults?.length);
    return {
      origin: extractFromMessages(/from|depart|leave|origin.*?([A-Z]{3})/i),
      destination: extractFromMessages(/to|arrive|destination.*?([A-Z]{3})/i),
      departureDate: extractFromMessages(/(?:on|depart|leave).*?(\d{4}-\d{2}-\d{2}|\w+ \d{1,2})/i),
      passengers: (() => {
        const raw = extractFromMessages(/(\d+)\s*(?:passenger|person|traveler|pax)/i);
        if (!raw) return undefined;
        const n = Number.parseInt(raw, 10);
        return Number.isFinite(n) ? n : undefined;
      })(),
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
  const journeyInfo = hasFlights ? extractJourneyInfo() : undefined;

  if (messages.length === 0 && !isLoading) {
    return <EmptyState />;
  }

  return (
    <div className="flex flex-1 gap-4 overflow-hidden">
      <ScrollArea className="flex-1" ref={scrollRef}>
        <div className="mx-auto max-w-4xl py-4 px-4">
          {/* Journey Summary */}
          {hasFlights && journeyInfo && <JourneySummary summary={journeyInfo} />}

          {/* Messages */}
          {messages.map((message) => (
            <MessageBubble 
              key={message.id} 
              message={{
                ...message,
                flightResults: filteredFlights && currentFlights === message.flightResults
                  ? filteredFlights
                  : message.flightResults
              }}
              userAvatar={user?.avatar}
              journeyInfo={journeyInfo}
              onShowFilter={() => {
                const nextFlights = message.flightResults || null;
                const isSameFlightList = currentFlights === nextFlights;
                setCurrentFlights(nextFlights);
                setShowFilter(true);
                // Preserve refinements when re-opening for the same flight list.
                // Reset only when switching to a different set of results.
                if (!isSameFlightList) {
                  setFilteredFlights(null);
                }
              }}
              onBooking={onBooking}
            />
          ))}
          {isLoading && <LoadingSkeleton />}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      {/* Flight Filter Panel */}
      {currentFlights && currentFlights.length > 0 && (
        <div className={showFilter ? "hidden lg:block w-80 border-l" : "hidden"}>
          <FlightFilter
            flights={currentFlights}
            onFilter={setFilteredFlights}
            onClose={() => setShowFilter(false)}
          />
        </div>
      )}
    </div>
  );
}
