import { useState, useRef, useEffect } from "react";
import { Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { ChatMessage } from "@shared/schema";
import type { CurrentPreferences } from "@/hooks/use-chat";

interface ChatInputProps {
  onSendMessage: (message: string, preferences?: CurrentPreferences) => void;
  isLoading?: boolean;
  disabled?: boolean;
  messages?: ChatMessage[];
  currentPreferences?: CurrentPreferences;
}

// Main suggested prompts - varied and interesting
const SUGGESTED_PROMPTS = [
  "Find flights from NYC to London next week",
  "What are my current travel preferences?",
  "I need a one-way ticket to Tokyo",
  "Search for cheap flights to Paris in December",
  "Find direct flights from LAX to Miami",
  "Show me weekend getaway options from my home city",
  "What routes do I travel most frequently?",
  "Find flights matching my travel preferences",
  "I'm planning a solo trip - what do you recommend?",
  "Search for business class flights to Singapore",
];

// Filter suggestions for after search results
const FILTER_SUGGESTIONS = [
  "Show me cheaper options",
  "I prefer direct flights only",
  "Find morning departure flights",
  "Show non-stop flights under $500",
  "Filter by my preferred airline",
  "Show me the fastest options",
  "What are my saved preferences?",
  "Exclude red-eyes",
];

// Helper function to get random suggestions without repetition
function getRandomSuggestions(suggestions: string[], count: number = 3): string[] {
  const shuffled = [...suggestions].sort(() => 0.5 - Math.random());
  return shuffled.slice(0, Math.min(count, suggestions.length));
}

export function ChatInput({ onSendMessage, isLoading, disabled, messages, currentPreferences }: ChatInputProps) {
  const [message, setMessage] = useState("");
  const [displayedSuggestions, setDisplayedSuggestions] = useState<string[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Initialize suggestions on mount
  useEffect(() => {
    const lastMessage = messages?.[messages.length - 1];
    const hasFlights = lastMessage?.flightResults && lastMessage.flightResults.length > 0;
    const suggestionPool = hasFlights ? FILTER_SUGGESTIONS : SUGGESTED_PROMPTS;
    setDisplayedSuggestions(getRandomSuggestions(suggestionPool, 3));
  }, [messages]);

  // Check if last message has flight results
  const lastMessage = messages?.[messages.length - 1];
  const hasFlights = lastMessage?.flightResults && lastMessage.flightResults.length > 0;
  const suggestions = displayedSuggestions.length > 0 ? displayedSuggestions : SUGGESTED_PROMPTS;

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [message]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !isLoading && !disabled) {
      onSendMessage(message.trim(), currentPreferences);
      setMessage("");
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleSuggestionClick = (prompt: string) => {
    if (!isLoading && !disabled) {
      onSendMessage(prompt, currentPreferences);
    }
  };

  return (
    <div className="sticky bottom-0 z-50 border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      {/* Quick Filter/Suggestion Buttons */}
      {suggestions.length > 0 && (
        <div className="border-b px-4 py-2 flex gap-2 overflow-x-auto scrollbar-hide">
          {suggestions.map((suggestion, idx) => (
            <Button
              key={idx}
              size="sm"
              variant="outline"
              onClick={() => handleSuggestionClick(suggestion)}
              disabled={isLoading || disabled}
              className="whitespace-nowrap text-xs"
            >
              {suggestion}
            </Button>
          ))}
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleSuggestionClick("Show my current preferences")}
            disabled={isLoading || disabled}
            className="whitespace-nowrap text-xs"
          >
            Show my current preferences
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleSuggestionClick("Show my travel history")}
            disabled={isLoading || disabled}
            className="whitespace-nowrap text-xs"
          >
            Show my travel history
          </Button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex items-end gap-2 p-4">
        <div className="relative flex-1">
          <Textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              hasFlights
                ? "Refine your search or ask for more options..."
                : "Ask me about flights, destinations, or travel plans..."
            }
            disabled={isLoading || disabled}
            className="min-h-[44px] max-h-[120px] resize-none pr-12"
            rows={1}
            data-testid="input-chat-message"
          />
          {message.length > 200 && (
            <span className="absolute bottom-2 right-12 text-xs text-muted-foreground">
              {message.length}/500
            </span>
          )}
        </div>

        <Button
          type="submit"
          size="icon"
          disabled={!message.trim() || isLoading || disabled}
          data-testid="button-send-message"
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
          <span className="sr-only">Send message</span>
        </Button>
      </form>
    </div>
  );
}
