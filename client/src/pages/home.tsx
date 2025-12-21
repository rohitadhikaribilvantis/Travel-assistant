import { useState, useEffect, useRef, useCallback } from "react";
import { ChatHeader } from "@/components/chat/chat-header";
import { ChatContainer } from "@/components/chat/chat-container";
import { ChatInput } from "@/components/chat/chat-input";
import { ConversationsSidebar } from "@/components/chat/conversations-sidebar";
import { useChat, type CurrentPreferences } from "@/hooks/use-chat";
import { useAuth } from "@/hooks/use-auth";

interface Conversation {
  id: string;
  title: string;
  archived: boolean;
  createdAt: string;
  updatedAt: string;
}

export default function Home() {
  const { token } = useAuth();
  const {
    messages,
    isLoading,
    sendMessage,
    clearChat,
    conversationId,
    setConversationId,
    loadConversation,
  } = useChat();

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loadingConversations, setLoadingConversations] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(256); // Default 256px (w-64)
  const [isResizing, setIsResizing] = useState(false);
  const [titleSavedForConv, setTitleSavedForConv] = useState<string | null>(null);
  const [isLoadingConversation, setIsLoadingConversation] = useState(false);
  const [preferencesRefreshTrigger, setPreferencesRefreshTrigger] = useState(0);
  const [currentPreferences, setCurrentPreferences] = useState<CurrentPreferences>({});
  const [refreshBookingsFn, setRefreshBookingsFn] = useState<(() => void) | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Update the refreshBookingsFn when chat-header passes the original function
  const handleRefreshBookings = useCallback((refreshFn: () => void) => {
    // Booking should only refresh travel history data; it should not trigger a chat prompt
    // or mutate chat messages (which can look like an automatic "show my preferences" action).
    setRefreshBookingsFn(() => refreshFn);
  }, []);

  // Trigger preference refresh after each message
  useEffect(() => {
    if (!isLoading && messages.length > 0) {
      // Refresh preferences when loading finishes
      setPreferencesRefreshTrigger(prev => prev + 1);
    }
  }, [isLoading, messages.length]);

  // Fetch conversations on mount or when token changes
  useEffect(() => {
    if (token) {
      setTitleSavedForConv(null); // Reset on login
      fetchConversations();
    } else {
      setConversations([]); // Clear conversations on logout
      setTitleSavedForConv(null);
      clearChat(); // Clear chat on logout
    }
  }, [token, clearChat]);

  // Auto-save conversation title when a new conversation is created with messages
  useEffect(() => {
    const saveConversationTitle = async () => {
      if (
        conversationId &&
        messages.length > 0 &&
        token &&
        !isLoadingConversation
      ) {
        // Skip if we've already saved a title for this conversation
        if (titleSavedForConv === conversationId) {
          return;
        }

        // Check if conversation already exists in the list
        const existingConv = conversations.find((c) => c.id === conversationId);
        if (existingConv) {
          // Conversation already exists with a title, don't auto-save
          // (it means it was loaded from the server, not newly created)
          setTitleSavedForConv(conversationId);
          return;
        }

        try {
          // Generate title from first user message
          const firstUserMessage = messages.find((m) => m.role === "user");
          if (!firstUserMessage?.content?.trim()) {
            return; // Don't save if no user message content
          }
          
          const title = firstUserMessage.content.substring(0, 60).trim();

          console.log(`Saving conversation ${conversationId} with title: ${title}`);

          // Create local conversation object to add to list immediately
          const newConversation: Conversation = {
            id: conversationId,
            title: title,
            archived: false,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          };

          // Add to local state immediately (optimistic update)
          setConversations((prev) => {
            const exists = prev.find((c) => c.id === conversationId);
            if (exists) {
              return prev.map((c) =>
                c.id === conversationId ? newConversation : c
              );
            }
            return [newConversation, ...prev];
          });

          // Save the title to backend
          const response = await fetch(
            `/api/conversations/${conversationId}/rename`,
            {
              method: "PUT",
              headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
              },
              body: JSON.stringify({ title }),
            }
          );

          if (response.ok) {
            console.log("Title saved successfully");
            setTitleSavedForConv(conversationId);
          } else {
            console.error("Failed to save title:", response.statusText);
          }
        } catch (error) {
          console.error("Failed to save conversation title:", error);
        }
      }
    };

    saveConversationTitle();
  }, [conversationId, messages, token, titleSavedForConv, isLoadingConversation, conversations]);

  const fetchConversations = async () => {
    if (!token) return;
    setLoadingConversations(true);
    try {
      const response = await fetch("/api/conversations", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setConversations(data);
        // If there are conversations, mark the first one as saved so auto-save won't overwrite
        if (data.length > 0) {
          setTitleSavedForConv(data[0].id);
        }
      }
    } catch (error) {
      console.error("Failed to fetch conversations:", error);
    } finally {
      setLoadingConversations(false);
    }
  };

  const handleNewConversation = async () => {
    // Save current conversation if it has messages and no ID
    if (messages.length > 0 && !conversationId && token) {
      try {
        // Generate title from first message or use default
        const title =
          messages[0]?.content?.substring(0, 50) || "New Conversation";
        
        // Create conversation via chat API by sending first message
        // The backend will create a new conversation automatically
        console.log("Creating new conversation with messages...");
      } catch (error) {
        console.error("Failed to save conversation:", error);
      }
    }

    // Clear for new chat (don't fetch - keep local state which has correct titles)
    clearChat();
    setTitleSavedForConv(null);
  };

  const handleSelectConversation = async (id: string) => {
    // Mark as already saved before loading so auto-save effect won't trigger
    setTitleSavedForConv(id);
    setIsLoadingConversation(true);
    try {
      await loadConversation(id);
    } finally {
      setIsLoadingConversation(false);
    }
  };

  const handleRenameConversation = async (id: string, title: string) => {
    if (!token) return;
    try {
      const response = await fetch(`/api/conversations/${id}/rename`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ title }),
      });
      if (response.ok) {
        // Update local state instead of fetching
        setConversations((prev) =>
          prev.map((c) =>
            c.id === id ? { ...c, title, updatedAt: new Date().toISOString() } : c
          )
        );
      }
    } catch (error) {
      console.error("Failed to rename conversation:", error);
    }
  };

  const handleDeleteConversation = async (id: string) => {
    if (!token) return;
    try {
      const response = await fetch(`/api/conversations/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        // Remove from local state instead of fetching
        setConversations((prev) => prev.filter((c) => c.id !== id));
        
        // If deleting the current conversation, start a new one
        if (id === conversationId) {
          handleNewConversation();
        }
      }
    } catch (error) {
      console.error("Failed to delete conversation:", error);
    }
  };

  const handleDeleteAllConversations = async (deletePreferences: boolean) => {
    if (!token) return;
    try {
      console.log("🗑️ [DELETE ALL] Starting deletion...");
      console.log(`🗑️ [DELETE ALL] deletePreferences: ${deletePreferences}`);
      
      // Delete all conversations
      const response = await fetch("/api/conversations", {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ deletePreferences }),
      });

      console.log(`🗑️ [DELETE ALL] Response status: ${response.status}`);

      if (response.ok) {
        const result = await response.json();
        console.log(`✅ [DELETE ALL] ${result.message}`);
        
        // Clear local state
        setConversations([]);
        handleNewConversation();
        
        // Auto-refresh conversations list
        console.log("🔄 [DELETE ALL] Refreshing conversations list...");
        setTimeout(() => {
          fetchConversations();
        }, 500);
      } else {
        const errorText = await response.text();
        console.error(`❌ [DELETE ALL] Failed: ${response.statusText}`);
        console.error(`❌ [DELETE ALL] Error details: ${errorText}`);
      }
    } catch (error) {
      console.error("❌ [DELETE ALL] Exception:", error);
    }
  };

  // Handle resize
  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;
      
      const container = containerRef.current;
      const rect = container.getBoundingClientRect();
      const newWidth = e.clientX - rect.left;

      // Min width 200px, max width 600px
      if (newWidth >= 200 && newWidth <= 600) {
        setSidebarWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizing]);

  return (
    <div ref={containerRef} className="flex h-screen">
      <div style={{ width: `${sidebarWidth}px` }} className="flex flex-col">
        <ConversationsSidebar
          conversations={conversations}
          activeConversationId={conversationId}
          onSelectConversation={handleSelectConversation}
          onNewConversation={handleNewConversation}
          onRenameConversation={handleRenameConversation}
          onDeleteConversation={handleDeleteConversation}
          onDeleteAllConversations={handleDeleteAllConversations}
        />
      </div>

      {/* Resize Divider */}
      <div
        onMouseDown={() => setIsResizing(true)}
        className={`w-1 bg-slate-700 hover:bg-blue-500 cursor-col-resize transition-colors ${
          isResizing ? "bg-blue-500" : ""
        }`}
      />

      <div className="flex flex-1 flex-col">
        <ChatHeader 
          onPreferencesRefresh={() => setPreferencesRefreshTrigger(prev => prev + 1)}
          externalRefreshTrigger={preferencesRefreshTrigger}
          onPreferencesChange={setCurrentPreferences}
          onRefreshBookings={handleRefreshBookings}
        />
        <ChatContainer
          messages={messages}
          isLoading={isLoading}
          isLoadingConversation={isLoadingConversation}
          onBooking={refreshBookingsFn || undefined}
        />
        <ChatInput onSendMessage={sendMessage} isLoading={isLoading} messages={messages} currentPreferences={currentPreferences} />
      </div>
    </div>
  );
}

