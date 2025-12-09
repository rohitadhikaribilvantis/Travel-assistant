import { Bot, User } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@shared/schema";
import { FlightCard } from "./flight-card";
import { Badge } from "@/components/ui/badge";

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isAssistant = message.role === "assistant";

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
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
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
          <Bot className="h-4 w-4 text-primary" />
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
            <p className="whitespace-pre-wrap text-sm leading-relaxed">
              {message.content}
            </p>
          )}
        </div>

        {message.flightResults && message.flightResults.length > 0 && (
          <div className="mt-2 flex w-full flex-col gap-4">
            {message.flightResults.map((flight, index) => (
              <FlightCard key={flight.id} flight={flight} index={index} />
            ))}
          </div>
        )}

        <span className="text-xs text-muted-foreground">
          {formatTimestamp(message.timestamp)}
        </span>
      </div>

      {isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary">
          <User className="h-4 w-4 text-secondary-foreground" />
        </div>
      )}
    </div>
  );
}
