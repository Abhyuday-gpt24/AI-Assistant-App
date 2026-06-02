import { FileIcon, MessageIcon, UserIcon } from "@/components/ui/icons";
import { cn } from "@/lib/cn";
import { MessageContent } from "./message-content";
import type { ChatMessage } from "./types";

export function MessageBubble({
  message,
  flash,
  streaming,
}: {
  message: ChatMessage;
  flash: boolean;
  streaming: boolean;
}) {
  const isUser = message.role === "user";
  return (
    <div
      className={cn(
        "flex items-start gap-3 transition-shadow",
        isUser && "flex-row-reverse",
        flash && "rounded-2xl ring-2 ring-(--ring)/60",
      )}
    >
      <div
        className={cn(
          "inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-accent text-accent-foreground",
        )}
        aria-hidden
      >
        {isUser ? (
          <UserIcon className="h-4 w-4" />
        ) : (
          <MessageIcon className="h-4 w-4" />
        )}
      </div>
      <div
        className={cn(
          "max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-foreground",
        )}
      >
        {streaming ? (
          <TypingDots />
        ) : isUser ? (
          <UserMessageBody message={message} />
        ) : (
          <MessageContent content={message.content} />
        )}
      </div>
    </div>
  );
}

function UserMessageBody({ message }: { message: ChatMessage }) {
  return (
    <div className="space-y-2">
      {message.attachments && message.attachments.length > 0 && (
        <ul className="flex flex-wrap gap-1.5">
          {message.attachments.map((att) => (
            <li
              key={att.storagePath}
              className="flex max-w-50 items-center gap-1.5 rounded-lg bg-(--primary-foreground)/15 px-2 py-1 text-xs"
            >
              <FileIcon className="h-3.5 w-3.5 shrink-0" />
              <span className="truncate" title={att.name}>
                {att.name}
              </span>
            </li>
          ))}
        </ul>
      )}
      {message.content && (
        <span className="block whitespace-pre-wrap">{message.content}</span>
      )}
    </div>
  );
}

function TypingDots() {
  return (
    <span className="inline-flex items-center gap-1 py-1" aria-label="Assistant is typing">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.3s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.15s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground" />
    </span>
  );
}
