import { User, Bot, Sliders } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import type { ChatMessage } from "@shared/schema";
import { FlightCard } from "./flight-card";
import { TravelHistoryDisplay } from "./travel-history-display";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface MessageBubbleProps {
  message: ChatMessage;
  userAvatar?: string;
  journeyInfo?: {
    passengers?: number;
    cabinClass?: string;
  };
  onShowFilter?: () => void;
  onBooking?: () => void;
}

export function MessageBubble({ message, userAvatar, journeyInfo, onShowFilter, onBooking }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isAssistant = message.role === "assistant";
  const hasFlights = message.flightResults && message.flightResults.length > 0;

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  // Group flights by tag category
  const groupFlightsByTag = (flights: typeof message.flightResults) => {
    if (!flights) return {};
    
    const groups: { [key: string]: typeof flights } = {
      cheapest: [],
      best: [],
      fastest: [],
      other: []
    };

    flights.forEach((flight) => {
      if (flight.tags?.includes("cheapest")) {
        groups.cheapest.push(flight);
      } else if (flight.tags?.includes("best")) {
        groups.best.push(flight);
      } else if (flight.tags?.includes("fastest")) {
        groups.fastest.push(flight);
      } else {
        groups.other.push(flight);
      }
    });

    return groups;
  };

  const getCategoryLabel = (category: string) => {
    switch (category) {
      case "cheapest":
        return "💰 Cheapest";
      case "best":
        return "🏆 Best Value";
      case "fastest":
        return "⚡ Fastest";
      case "other":
        return "Other Options";
      default:
        return category;
    }
  };

  return (
    <div
      className={cn(
        "flex gap-3 px-4 py-2",
        isUser ? "justify-end" : "justify-start"
      )}
      data-testid={`message-${message.role}-${message.id}`}
    >
      {isAssistant && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-200">
          <Bot className="h-4 w-4 text-slate-600" />
        </div>
      )}

      {isUser && userAvatar && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full overflow-hidden order-2">
          <Avatar className="h-8 w-8">
            <AvatarImage src={userAvatar} alt="User avatar" />
            <AvatarFallback>
              <User className="h-4 w-4" />
            </AvatarFallback>
          </Avatar>
        </div>
      )}

      {isUser && !userAvatar && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 order-2">
          <User className="h-4 w-4 text-blue-600" />
        </div>
      )}

      <div
        className={cn(
          "flex max-w-2xl flex-col gap-2",
          isUser && "items-end"
        )}
      >
        {message.memoryContext && (
          <Badge variant="secondary" className="text-xs">
            {message.memoryContext}
          </Badge>
        )}

        {message.appliedPrefs && (
          <Badge variant="outline" className="text-xs text-muted-foreground">
            Since you prefer: {message.appliedPrefs}
          </Badge>
        )}

        <div
          className={cn(
            "rounded-2xl px-4 py-3",
            isUser
              ? "bg-primary text-primary-foreground"
              : "bg-card border border-card-border"
          )}
        >
          {message.isStreaming ? (
            <div className="flex items-center gap-1">
              <span className="animate-pulse">{message.content}</span>
              <span className="inline-flex gap-1">
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current [animation-delay:-0.3s]" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current [animation-delay:-0.15s]" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current" />
              </span>
            </div>
          ) : (
            <div className="prose prose-sm max-w-none text-sm leading-relaxed dark:prose-invert prose-headings:mt-3 prose-headings:mb-2 prose-h1:text-base prose-h2:text-sm prose-h3:text-xs prose-p:my-1 prose-ul:my-1 prose-li:my-0 prose-strong:font-semibold prose-code:bg-secondary prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-pre:bg-secondary prose-pre:p-3 prose-pre:overflow-x-auto">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>

        {hasFlights && (
          <div className="mt-2 w-full space-y-4">
            {/* Filter Button */}
            {onShowFilter && (
              <Button
                size="sm"
                variant="outline"
                onClick={onShowFilter}
                className="w-full gap-2"
              >
                <Sliders className="h-4 w-4" />
                Refine Results
              </Button>
            )}

            {/* Grouped Flight Cards */}
            {(() => {
              const flightGroups = groupFlightsByTag(message.flightResults);
              const categoryOrder = ["best", "cheapest", "fastest", "other"];
              
              return (
                <div className="space-y-6">
                  {categoryOrder.map((category) => {
                    const flights = flightGroups[category];
                    if (!flights || flights.length === 0) return null;
                    
                    return (
                      <div key={category} className="space-y-3">
                        <h3 className="text-sm font-semibold text-muted-foreground">
                          {getCategoryLabel(category)}
                        </h3>
                        <div className="flex flex-col gap-4">
                          {flights.map((flight, index) => (
                            <FlightCard
                              key={`${flight.id}-${index}`}
                              flight={flight}
                              index={index}
                              passengers={journeyInfo?.passengers}
                              onBooking={onBooking}
                            />
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              );
            })()}
          </div>
        )}

        {message.travelHistory && message.travelHistory.length > 0 && (
          <div className="mt-3 w-full">
            <TravelHistoryDisplay bookings={message.travelHistory} />
          </div>
        )}

        <span className="text-xs text-muted-foreground">
          {formatTimestamp(message.timestamp)}
        </span>
      </div>
    </div>
  );
}
