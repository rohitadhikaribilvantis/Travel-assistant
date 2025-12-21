import { useState, useCallback } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import type { ChatMessage, ChatResponse } from "@shared/schema";
import { useAuth } from "./use-auth";

export interface CurrentPreferences {
  directFlightsOnly?: boolean;
  avoidRedEye?: boolean;
  cabinClass?: string;
  preferredTime?: string;
  tripType?: string;
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const { token, user } = useAuth();

  const sendMessageMutation = useMutation({
    mutationFn: async ({ message, preferences }: { message: string; preferences?: CurrentPreferences }): Promise<any> => {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: token ? `Bearer ${token}` : "",
        },
        body: JSON.stringify({
          message,
          conversationId,
          currentPreferences: preferences,
        }),
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(error || "Failed to send message");
      }

      return response.json();
    },
    onSuccess: (data) => {
      setConversationId(data.conversationId);
      
      // Add assistant message with streaming effect
      const assistantMessage: ChatMessage = {
        ...data.message,
        isStreaming: true,
      };
      
      setMessages((prev) => [...prev, assistantMessage]);
      
      // Simulate streaming by updating message gradually
      const chunks = data.message.content.split(" ");
      let currentIndex = 0;
      
      const streamInterval = setInterval(() => {
        if (currentIndex < chunks.length) {
          const streamedContent = chunks.slice(0, currentIndex + 3).join(" ");
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === data.message.id
                ? { ...msg, content: streamedContent, isStreaming: true }
                : msg
            )
          );
          currentIndex += 3;
        } else {
          clearInterval(streamInterval);
          // Mark as finished streaming
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === data.message.id
                ? { ...msg, isStreaming: false }
                : msg
            )
          );
        }
      }, 50);
      
      // Store extracted preferences in localStorage so ChatHeader can pick them up
      if (data.extractedPreferences && data.extractedPreferences.length > 0 && user?.id) {
        localStorage.setItem(
          `new_preferences_${user.id}`,
          JSON.stringify(data.extractedPreferences)
        );

        // Also dispatch an in-tab event so listeners can refresh immediately.
        // (The 'storage' event does not fire in the same document that setItem runs in.)
        window.dispatchEvent(
          new CustomEvent("skymate:preferences-updated", {
            detail: { extractedPreferences: data.extractedPreferences },
          })
        );
      }
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
    (content: string, preferences?: CurrentPreferences) => {
      const userMessage: ChatMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);
      sendMessageMutation.mutate({ message: content, preferences });
    },
    [sendMessageMutation]
  );

  const clearChat = useCallback(() => {
    setMessages([]);
    setConversationId(undefined);
  }, []);

  const loadConversation = useCallback(
    async (convId: string) => {
      if (!token) return;
      try {
        const response = await fetch(`/api/conversations/${convId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (response.ok) {
          const data = await response.json();
          setConversationId(convId);
          // Sort messages by timestamp (oldest first)
          const sortedMessages = (data.messages || []).sort((a: ChatMessage, b: ChatMessage) => 
            new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
          );
          setMessages(sortedMessages);
        }
      } catch (error) {
        console.error("Failed to load conversation:", error);
      }
    },
    [token]
  );

  return {
    messages,
    setMessages,
    isLoading: sendMessageMutation.isPending,
    sendMessage,
    clearChat,
    loadConversation,
    error: sendMessageMutation.error,
    conversationId,
    setConversationId,
  };
}
