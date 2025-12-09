import { Plane, Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";

interface ChatHeaderProps {
  onNewChat?: () => void;
}

export function ChatHeader({ onNewChat }: ChatHeaderProps) {
  return (
    <header className="sticky top-0 z-50 flex h-16 items-center justify-between gap-4 border-b bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/60 md:px-6">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary">
          <Plane className="h-5 w-5 text-primary-foreground" />
        </div>
        <div className="flex flex-col">
          <h1 className="text-lg font-semibold leading-tight">SkyMate</h1>
          <p className="text-xs text-muted-foreground">AI Travel Assistant</p>
        </div>
      </div>
      
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={onNewChat}
          data-testid="button-new-chat"
          className="hidden sm:flex"
        >
          New Chat
        </Button>
        <Button
          variant="ghost"
          size="icon"
          data-testid="button-settings"
        >
          <Settings className="h-5 w-5" />
          <span className="sr-only">Settings</span>
        </Button>
        <ThemeToggle />
      </div>
    </header>
  );
}
