import { useState } from "react";
import { Trash2, MoreVertical, Plus, Edit2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";

interface Conversation {
  id: string;
  title: string;
  archived: boolean;
  createdAt: string;
  updatedAt: string;
}

interface ConversationsSidebarProps {
  conversations: Conversation[];
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewConversation: () => void;
  onRenameConversation: (id: string, title: string) => void;
  onDeleteConversation: (id: string) => void;
}

export function ConversationsSidebar({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  onRenameConversation,
  onDeleteConversation,
}: ConversationsSidebarProps) {
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [newTitle, setNewTitle] = useState("");

  const handleRename = (id: string, currentTitle: string) => {
    setRenamingId(id);
    setNewTitle(currentTitle);
  };

  const handleSaveRename = (id: string) => {
    if (newTitle.trim()) {
      onRenameConversation(id, newTitle);
      setRenamingId(null);
    }
  };

  const filteredConversations = conversations.filter(
    (conv) => !conv.archived
  );

  return (
    <div className="w-full bg-slate-900 text-white flex flex-col h-screen border-r border-slate-700">
      {/* Header */}
      <div className="p-4 border-b border-slate-700">
        <Button
          onClick={onNewConversation}
          className="w-full bg-slate-700 hover:bg-slate-600"
        >
          <Plus className="w-4 h-4 mr-2" />
          New Chat
        </Button>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto">
        {filteredConversations.length === 0 ? (
          <div className="p-4 text-slate-400 text-sm text-center">
            No conversations yet
          </div>
        ) : (
          <div className="space-y-2 p-2">
            {filteredConversations.map((conv) => (
              <div
                key={conv.id}
                className={`group relative rounded-lg p-3 cursor-pointer transition-colors ${
                  activeConversationId === conv.id
                    ? "bg-slate-700"
                    : "hover:bg-slate-800"
                }`}
                onClick={() => onSelectConversation(conv.id)}
              >
                {renamingId === conv.id ? (
                  <Input
                    autoFocus
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                    onBlur={() => handleSaveRename(conv.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleSaveRename(conv.id);
                      if (e.key === "Escape") setRenamingId(null);
                    }}
                    onClick={(e) => e.stopPropagation()}
                    className="h-9 text-sm bg-slate-800 border-slate-600 px-2"
                  />
                ) : (
                  <>
                    <div className="text-sm font-medium truncate pr-8">
                      {conv.title || "New Conversation"}
                    </div>
                    <div className="text-xs text-slate-400 mt-1">
                      {new Date(conv.updatedAt).toLocaleDateString()}
                    </div>
                  </>
                )}

                {/* Actions Menu */}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button
                      className="absolute right-2 top-3 opacity-0 group-hover:opacity-100 transition-opacity p-1"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <MoreVertical className="w-4 h-4" />
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-48">
                    <DropdownMenuItem
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRename(conv.id, conv.title);
                      }}
                    >
                      <Edit2 className="w-4 h-4 mr-2" />
                      Rename
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      className="text-red-400 focus:text-red-300"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (
                          window.confirm(
                            "Are you sure you want to delete this conversation?"
                          )
                        ) {
                          onDeleteConversation(conv.id);
                        }
                      }}
                    >
                      <Trash2 className="w-4 h-4 mr-2" />
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            ))}
          </div>
        )}
      </div>

    </div>
  );
}
