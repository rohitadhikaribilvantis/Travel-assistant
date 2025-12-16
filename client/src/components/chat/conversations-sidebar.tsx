import { useState } from "react";
import { Trash2, MoreVertical, Plus, Edit2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";

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
  onDeleteAllConversations?: (deletePreferences: boolean) => void;
}

export function ConversationsSidebar({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  onRenameConversation,
  onDeleteConversation,
  onDeleteAllConversations,
}: ConversationsSidebarProps) {
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const [showDeleteAllDialog, setShowDeleteAllDialog] = useState(false);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [deletePreferencesToo, setDeletePreferencesToo] = useState(false);

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
      <div className="p-4 border-b border-slate-700 space-y-2">
        <div className="flex gap-2">
          <Button
            onClick={onNewConversation}
            className="flex-1 bg-slate-700 hover:bg-slate-600"
          >
            <Plus className="w-4 h-4 mr-2" />
            New Chat
          </Button>
          <Button
            onClick={() => setShowDeleteAllDialog(true)}
            variant="ghost"
            className="px-3 hover:bg-slate-700 hover:text-red-400"
            title="Delete all chats"
          >
            <Trash2 className="w-4 h-4" />
          </Button>
        </div>
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

      {/* Delete All Dialog - Step 1: Choose preferences option */}
      <AlertDialog open={showDeleteAllDialog && !showConfirmDialog} onOpenChange={setShowDeleteAllDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete All Chats</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete all your chat conversations? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          
          <div className="py-4 space-y-3">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="delete-prefs"
                checked={deletePreferencesToo}
                onCheckedChange={(checked) => setDeletePreferencesToo(checked as boolean)}
              />
              <Label htmlFor="delete-prefs" className="font-normal text-sm cursor-pointer">
                Also delete all my travel preferences?
              </Label>
            </div>
          </div>

          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            className="bg-red-600 hover:bg-red-700"
            onClick={() => {
              setShowConfirmDialog(true);
            }}
          >
            Continue
          </AlertDialogAction>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete All Dialog - Step 2: Final confirmation */}
      <AlertDialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
            <AlertDialogDescription className="space-y-2">
              <p>This will permanently delete:</p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>All chat conversations</li>
                {deletePreferencesToo && <li>All travel preferences</li>}
              </ul>
              <p className="font-semibold text-red-500 mt-3">This action cannot be undone!</p>
            </AlertDialogDescription>
          </AlertDialogHeader>

          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            className="bg-red-600 hover:bg-red-700"
            onClick={() => {
              console.log("🗑️ [SIDEBAR] Delete Everything clicked!");
              console.log("🗑️ [SIDEBAR] deletePreferencesToo:", deletePreferencesToo);
              console.log("🗑️ [SIDEBAR] onDeleteAllConversations:", typeof onDeleteAllConversations);
              if (onDeleteAllConversations) {
                console.log("🗑️ [SIDEBAR] Calling onDeleteAllConversations...");
                onDeleteAllConversations(deletePreferencesToo);
              } else {
                console.error("❌ [SIDEBAR] onDeleteAllConversations is not defined!");
              }
              setShowConfirmDialog(false);
              setShowDeleteAllDialog(false);
              setDeletePreferencesToo(false);
            }}
          >
            Delete Everything
          </AlertDialogAction>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
