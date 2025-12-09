import { useEffect, useRef } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageBubble } from "./message-bubble";
import { EmptyState } from "./empty-state";
import { LoadingSkeleton } from "./loading-skeleton";
import type { ChatMessage } from "@shared/schema";

interface ChatContainerProps {
  messages: ChatMessage[];
  isLoading?: boolean;
}

export function ChatContainer({ messages, isLoading }: ChatContainerProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isLoading]);

  if (messages.length === 0 && !isLoading) {
    return <EmptyState />;
  }

  return (
    <ScrollArea className="flex-1" ref={scrollRef}>
      <div className="mx-auto max-w-4xl py-4">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        {isLoading && <LoadingSkeleton />}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
