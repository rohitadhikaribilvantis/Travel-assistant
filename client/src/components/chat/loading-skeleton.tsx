import { Bot } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

export function LoadingSkeleton() {
  return (
    <div className="flex gap-3 px-4 py-2">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
        <Bot className="h-4 w-4 text-primary" />
      </div>

      <div className="flex max-w-2xl flex-col gap-2">
        <div className="rounded-2xl bg-card border border-card-border px-4 py-3">
          <div className="flex items-center gap-1">
            <span className="inline-flex gap-1">
              <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:-0.3s]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:-0.15s]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground/50" />
            </span>
            <span className="ml-2 text-sm text-muted-foreground">
              Thinking...
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

export function FlightCardSkeleton() {
  return (
    <div className="w-full rounded-lg border bg-card p-4 md:p-6">
      <div className="flex flex-col gap-4">
        <div className="flex gap-2">
          <Skeleton className="h-5 w-16" />
          <Skeleton className="h-5 w-16" />
        </div>

        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-1 flex-col gap-4">
            <div className="flex items-center gap-4">
              <Skeleton className="h-10 w-10 rounded-full" />
              <div className="flex flex-col gap-1">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-3 w-16" />
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex flex-col items-center gap-1">
                <Skeleton className="h-6 w-12" />
                <Skeleton className="h-4 w-8" />
                <Skeleton className="h-3 w-10" />
              </div>

              <div className="flex flex-1 flex-col items-center gap-1">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-px w-full" />
                <Skeleton className="h-3 w-12" />
              </div>

              <div className="flex flex-col items-center gap-1">
                <Skeleton className="h-6 w-12" />
                <Skeleton className="h-4 w-8" />
                <Skeleton className="h-3 w-10" />
              </div>
            </div>
          </div>

          <div className="flex flex-col items-end gap-2 border-t pt-4 md:border-l md:border-t-0 md:pl-6 md:pt-0">
            <Skeleton className="h-8 w-24" />
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-5 w-14" />
            <Skeleton className="h-9 w-20 mt-2" />
          </div>
        </div>
      </div>
    </div>
  );
}
