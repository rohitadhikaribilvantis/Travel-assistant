import { ChatHeader } from "@/components/chat/chat-header";
import { ChatContainer } from "@/components/chat/chat-container";
import { ChatInput } from "@/components/chat/chat-input";
import { useChat } from "@/hooks/use-chat";

export default function Home() {
  const { messages, isLoading, sendMessage, clearChat } = useChat();

  return (
    <div className="flex h-screen flex-col">
      <ChatHeader onNewChat={clearChat} />
      <ChatContainer messages={messages} isLoading={isLoading} />
      <ChatInput onSendMessage={sendMessage} isLoading={isLoading} />
    </div>
  );
}
