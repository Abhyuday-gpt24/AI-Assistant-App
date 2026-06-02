import { MessageIcon } from "@/components/ui/icons";
import { cn } from "@/lib/cn";

export function HistorySkeleton() {
  return (
    <ul className="space-y-5" aria-busy="true" aria-label="Loading chat history">
      {[0, 1, 2].map((i) => (
        <li key={i} className={cn("flex items-start gap-3", i % 2 === 0 && "flex-row-reverse")}>
          <div className="h-8 w-8 shrink-0 animate-pulse rounded-full bg-muted" />
          <div className="h-12 w-2/3 animate-pulse rounded-2xl bg-muted" />
        </li>
      ))}
    </ul>
  );
}

export function HistoryError({ message }: { message: string }) {
  return (
    <div
      role="alert"
      className="rounded-md border border-border bg-muted px-3 py-2 text-sm text-foreground"
    >
      Couldn&apos;t load chat history: {message}
    </div>
  );
}

export function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-accent text-accent-foreground">
        <MessageIcon className="h-6 w-6" />
      </div>
      <h3 className="text-base font-semibold">Start a new conversation</h3>
      <p className="mt-1 max-w-sm text-sm text-muted-foreground">
        Ask a question, paste content, or describe what you&apos;d like help with.
      </p>
    </div>
  );
}
