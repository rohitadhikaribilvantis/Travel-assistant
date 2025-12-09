import { useState, useCallback } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import type { ChatMessage, ChatResponse } from "@shared/schema";

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>();

  const sendMessageMutation = useMutation({
    mutationFn: async (message: string): Promise<ChatResponse> => {
      const response = await apiRequest("POST", "/api/chat", {
        message,
        conversationId,
        userId: "default-user",
      });
      return response.json();
    },
    onSuccess: (data) => {
      setConversationId(data.conversationId);
      setMessages((prev) => [...prev, data.message]);
    },
    onError: (error) => {
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content: `I apologize, but I encountered an error: ${error.message}. Please try again.`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    },
  });

  const sendMessage = useCallback(
    (content: string) => {
      const userMessage: ChatMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);
      sendMessageMutation.mutate(content);
    },
    [sendMessageMutation]
  );

  const clearChat = useCallback(() => {
    setMessages([]);
    setConversationId(undefined);
  }, []);

  return {
    messages,
    isLoading: sendMessageMutation.isPending,
    sendMessage,
    clearChat,
    error: sendMessageMutation.error,
  };
}
