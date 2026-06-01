@AGENTS.md

# AI Doc Assist — Project Guide

Next.js 16 frontend for an AI document assistant. It talks to a **FastAPI backend** (default `http://localhost:8000`) over REST + Server-Sent Events for auth, chats, and streaming replies. **Auth and chats are live**; **projects are still dummy** (`lib/projects.ts`). All network access goes through the typed client layer in `lib/api/`.

## Critical conventions

- **Next.js 16 (App Router) + React 19**. APIs and file conventions differ from older versions. Before writing routing/data code, consult `node_modules/next/dist/docs/01-app/`.
- **`params` and `searchParams` are Promises** in pages/layouts — always `await` them (e.g. `const { id } = await params`).
- **Strict TypeScript** (`tsconfig.json` → `strict: true`). No `any`. No `@ts-ignore`.
- **Path alias** `@/*` resolves to the repo root (so `@/components/...`, `@/lib/...`).
- **Tailwind v4** via `@tailwindcss/postcss`. Dark mode is **class-based**, opted in via `@custom-variant dark (&:where(.dark, .dark *))` in `app/globals.css`. Theme tokens are CSS custom properties on `:root` / `.dark`; use them as `bg-[var(--background)]`, `text-[var(--foreground)]`, etc.
- **Server vs Client Components**: layouts/pages are Server Components by default. Mark a file `"use client"` only when it needs state, effects, browser APIs, or event handlers. Push the boundary as deep as possible (e.g. the auth `page.tsx` is server, the form inside it is client).
- **Route groups** `(auth)` and `(app)` exist only to share layouts — they don't appear in URLs.
- **No external UI/icon libraries.** Buttons, inputs, icons are hand-rolled inline SVG components in `components/ui/`. The **one** sanctioned content dependency is `react-markdown` (+ `remark-gfm`), used solely to render assistant replies in `components/chat/message-content.tsx` — don't reach for UI kits beyond that.
- **All backend calls go through `lib/api/*`.** Never `fetch` a backend route directly from a component — use the typed helpers (`apiFetch` wrapper + per-domain modules). They handle the base URL, cookie credentials, and 401 → `/login` bouncing.

## Tech stack

| Concern        | Choice                                                          |
| -------------- | --------------------------------------------------------------- |
| Framework      | Next.js 16.2.6 (App Router, Turbopack)                          |
| UI runtime     | React 19.2.4                                                    |
| Language       | TypeScript 5 (strict)                                           |
| Styling        | Tailwind CSS v4 + CSS custom properties for theming             |
| Markdown       | `react-markdown` 10 + `remark-gfm` 4 (assistant replies only)  |
| Backend API    | FastAPI at `NEXT_PUBLIC_API_BASE_URL` (default `localhost:8000`) |
| Auth           | httpOnly session cookie (`credentials: "include"`); user profile cached in `localStorage` |
| Package mgr    | pnpm (see `pnpm-lock.yaml`, `pnpm-workspace.yaml`)              |
| Lint           | ESLint 9 + `eslint-config-next`                                 |

## Directory structure

```
ai-doc-assist/
├── app/                              # App Router root
│   ├── layout.tsx                    # Root layout: ThemeScript (head); ThemeProvider → AuthProvider (body)
│   ├── page.tsx                      # "/" → redirect("/login")
│   ├── globals.css                   # Tailwind import, dark variant, emerald design tokens, body styles
│   ├── favicon.ico
│   │
│   ├── (auth)/                       # Route group: unauthenticated pages
│   │   ├── layout.tsx                # Centered card layout + floating ThemeToggle
│   │   ├── login/
│   │   │   ├── page.tsx              # Server: text + <LoginForm />
│   │   │   └── login-form.tsx        # "use client": calls login() → setUser → router.push("/chat")
│   │   └── signup/
│   │       ├── page.tsx
│   │       └── signup-form.tsx       # "use client": calls signup() → setUser → router.push("/chat")
│   │
│   └── (app)/                        # Route group: authenticated shell
│       ├── layout.tsx                # Renders <Shell title="Chat">{children}</Shell>
│       ├── chat/
│       │   ├── page.tsx              # New empty chat → <ChatWindow title="New chat" />
│       │   └── [id]/page.tsx         # Server, awaits params → <ChatWindow chatId={id} />
│       └── projects/
│           ├── page.tsx              # Projects grid (dummy)
│           └── [id]/page.tsx         # Project detail stub (dummy)
│
├── components/
│   ├── auth/
│   │   └── auth-provider.tsx         # "use client": useAuth() context; caches user profile in localStorage["auth_user"]
│   │
│   ├── theme/
│   │   ├── theme-provider.tsx        # "use client": context for theme/resolvedTheme/setTheme/toggleTheme
│   │   ├── theme-script.tsx          # Inline <script> that runs before hydration to prevent FOUC
│   │   └── theme-toggle.tsx          # 3-state segmented control: Light / System / Dark
│   │
│   ├── shell/
│   │   ├── shell.tsx                 # "use client": owns sidebar collapsed + mobileOpen state
│   │   ├── sidebar.tsx               # "use client": title → New chat → Projects → Search → Recent chats → Footer
│   │   ├── header.tsx                # "use client": mobile menu button + ThemeToggle + sign-out (NO collapse btn)
│   │   └── footer.tsx                # Static disclaimer footer
│   │
│   ├── chat/
│   │   ├── chat-window.tsx           # "use client": loads history, sends via streamChat, scroll/jump/flash
│   │   ├── chatbox.tsx               # "use client": auto-grow textarea (max-w-4xl, text-base), Enter to send
│   │   ├── message-content.tsx       # Renders assistant markdown (react-markdown + remark-gfm), token-themed
│   │   ├── checkpointer.tsx          # "use client": right-rail navigator; hover to expand, click to jump
│   │   └── types.ts                  # ChatMessage type { id, role, content, createdAt }
│   │
│   └── ui/
│       ├── button.tsx                # forwardRef'd button; variants: primary | outline | ghost; sizes: sm | md | icon
│       ├── input.tsx                 # forwardRef'd input
│       ├── label.tsx                 # styled <label>
│       └── icons.tsx                 # Inline SVG icons: Menu, Sidebar, Plus, Send, Message, Search, Close,
│                                     # Logout, Settings, User, Folder, FolderPlus, ChevronRight
│
├── lib/
│   ├── api/
│   │   ├── client.ts                 # API_BASE_URL, apiFetch (credentials + 401→/login), ApiError, parseError
│   │   ├── auth.ts                   # signup / login / logout; User, AuthResponse types
│   │   ├── chats.ts                  # getChats / getMessages; ChatListItem, MessageItem types (no createChat!)
│   │   └── chat.ts                   # streamChat() SSE reader + parseFrame (chat_id/delta/error/[DONE])
│   ├── cn.ts                         # tiny classnames combinator (no deps)
│   └── projects.ts                   # ProjectSummary type + DUMMY_PROJECTS (still dummy)
│
├── public/                           # Static assets (next.svg, vercel.svg, etc.)
│
├── AGENTS.md                         # ⚠ Loaded first — "this is not the Next.js you know" warning
├── CLAUDE.md                         # This file
├── next.config.ts                    # NextConfig (empty/default)
├── next-env.d.ts                     # Next.js type augmentations (generated)
├── tsconfig.json                     # strict TS, paths: { "@/*": ["./*"] }
├── postcss.config.mjs                # { plugins: { "@tailwindcss/postcss": {} } }
├── eslint.config.mjs                 # eslint-config-next
├── package.json
├── pnpm-lock.yaml
├── pnpm-workspace.yaml
└── README.md
```

## Routing map

| URL                    | File                                  | Render |
| ---------------------- | ------------------------------------- | ------ |
| `/`                    | `app/page.tsx` (redirects to `/login`) | static |
| `/login`               | `app/(auth)/login/page.tsx`           | static |
| `/signup`              | `app/(auth)/signup/page.tsx`          | static |
| `/chat`                | `app/(app)/chat/page.tsx`             | static |
| `/chat/[id]`           | `app/(app)/chat/[id]/page.tsx`        | dynamic |
| `/projects`            | `app/(app)/projects/page.tsx`         | static |
| `/projects/[id]`       | `app/(app)/projects/[id]/page.tsx`    | dynamic |

`(auth)` and `(app)` are route groups — the parentheses don't appear in URLs.

## Backend / API integration

- **Base URL**: `lib/api/client.ts` → `API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"`. All paths are prefixed `/api/...`.
- **`apiFetch(path, init)`**: the single wrapped `fetch`. Always sends `credentials: "include"` (the httpOnly session cookie). On a `401` (when not already on `/login`/`/signup`) it hard-redirects to `/login`. Errors are normalized to `ApiError` via `parseError` (reads FastAPI's `{ detail }`).
- **Auth**: `auth.ts` exposes `signup` / `login` / `logout`. The session lives in an httpOnly cookie the JS can't read, so `AuthProvider` separately caches the **user profile** in `localStorage["auth_user"]` just to render the name after a refresh. `useAuth()` gives `{ user, setUser }`.
- **Endpoint map** (backend, all under `/api`):
  | Frontend call            | Method & route                  |
  | ------------------------ | ------------------------------- |
  | `signup` / `login` / `logout` | `POST /api/auth/{signup,login,logout}` |
  | `getChats()`             | `GET  /api/chats`               |
  | `getMessages(id)`        | `GET  /api/chats/{id}/messages` |
  | `streamChat(body)`       | `POST /api/chat/stream` (SSE)   |
- **⚠ There is no `POST /api/chats`.** A new chat is created **implicitly** by the backend when `streamChat` is called **without** a `chat_id`. Do not add a "create chat" call — it 405s.

### SSE streaming contract (`streamChat` ↔ `POST /api/chat/stream`)

The response is `text/event-stream`. `streamChat` reads the body, splits on `\n\n`, and runs each frame's `data:` JSON through `parseFrame`:

| Frame                       | Meaning                          | Handling                                  |
| --------------------------- | -------------------------------- | ----------------------------------------- |
| `{"chat_id": "..."}`        | id of the (possibly new) chat; sent **first** | fires `onChatId` → deep-link the URL |
| `{"delta": "..."}`          | incremental slice of the reply   | fires `onChunk` (appended to the bubble)  |
| `{"error": "..."}`          | server-side failure (terminal)   | **thrown** → surfaced as `⚠ <message>`    |
| `[DONE]` (bare sentinel)    | stream complete                  | fires `onDone`                            |

Unknown/non-JSON frames fall back to raw text. When adding stream features, extend `parseFrame` + `StreamChatOptions`, not the call sites.

## Theming

- **Source of truth**: CSS custom properties on `:root` (light defaults) and `.dark` (overrides) in `app/globals.css`.
- **Tokens**: `--background`, `--foreground`, `--muted`, `--muted-foreground`, `--card`, `--card-foreground`, `--border`, `--input`, `--primary`, `--primary-foreground`, `--accent`, `--accent-foreground`, `--ring`.
- **Palette = emerald accent, both themes.** `--primary`/`--ring` are emerald (light `#059669`, dark brighter `#10b981`) and drive interactive surfaces: buttons, the **user** message bubble, markdown links, focus rings. `--accent` is a soft mint (light) / deep green (dark) for sidebar hover/active rows. Light surfaces are a **faint-mint off-white** (no stark `#fff`, to reduce eye strain) with a tinted `--card` rail; dark backgrounds carry a faint green cast. Surface hierarchy: `card`/`background`/`muted`/`border`. Tune colours by editing the token values only — components never hardcode colour.
- **Tailwind binding**: `@theme inline` maps these to `--color-*` so utilities like `bg-primary`/`text-foreground` work, *and* arbitrary syntax `bg-[var(--background)]` works everywhere.
- **Dark variant**: `@custom-variant dark (&:where(.dark, .dark *))` — `dark:` utilities apply when an ancestor has `.dark`.
- **Preference**: stored in `localStorage["theme"]` as `"light" | "dark"`. Absence = `"system"`. Default is **system** (follows `prefers-color-scheme`).
- **No-flash**: `<ThemeScript />` runs synchronously in `<head>` before hydration to add/remove `.dark` on `<html>` based on storage or system.
- **Live system changes**: when preference is `system`, `ThemeProvider` listens to `matchMedia("(prefers-color-scheme: dark)")` and re-applies.

## Shell layout behavior

- **Sidebar** has two responsive modes (see `components/shell/sidebar.tsx`):
  - **Mobile (`<md`)**: hidden by default. Tapping the header **menu** icon sets `mobileOpen = true`, sliding the sidebar in with a backdrop. Tapping the backdrop, a chat, or the close icon closes it.
  - **Desktop (`>=md`)**: always visible, toggles between expanded (`w-72`) and collapsed (`w-16`, icon-only) via `collapsed` state in `Shell`.
- **The collapse toggle lives only in the sidebar header** (`SidebarHeader`). `header.tsx` keeps only the mobile menu button — there is intentionally **no** collapse button in the top header (it was a duplicate).
- **State ownership**: `Shell` owns `collapsed` and `mobileOpen`. Header gets `onOpenMobile`; Sidebar gets `onToggleCollapsed` + `onCloseMobile`.
- **Sidebar order**: title ("AI Doc Assist", no logo icon) → New chat → **ProjectsSection** → Search → Recent chats list → SidebarFooter. ProjectsSection has a top border to separate from New chat.
- **Collapsed (`w-16`) shows icons only**, deliberately pruned to avoid stacks of identical glyphs:
  - New chat → `Plus` icon (emerald, `title="New chat"` tooltip).
  - Projects → **just** the New-project `FolderPlus` icon (`title="New project"`); the individual project rows, the Projects header, and Search are hidden.
  - Recent chats list is **hidden entirely** (icon-only chat rows aren't useful); its `<nav>` stays as the flex spacer so `SidebarFooter` remains pinned to the bottom.
- **Collapse-aware pattern**: center + drop padding with `collapsed && "md:justify-center md:px-0"`, hide labels with `collapsed && "md:hidden"`, and add a `title` so the bare icon has a tooltip.

## Chat behavior

- `ChatWindow` (`components/chat/chat-window.tsx`) holds messages in local state. With a `chatId` it loads history via `getMessages(id)` on mount; the index route (`/chat`) starts empty.
- **Sending** appends a user bubble + an empty assistant bubble, then calls `streamChat`. `onChunk` appends each delta to the assistant bubble (typing dots while it's still empty).
- **New-chat flow**: when there's no `chatId`, `streamChat` is sent **without** one and the backend creates the chat. The `chat_id` frame arrives first → `applyChatId` sets `chatIdRef`, soft-updates the URL with `history.replaceState` (no router push, so the in-flight stream isn't torn down), and dispatches a `chats:changed` event to refresh the sidebar. If that frame never comes (older backend), a post-stream `getChats()` fallback recovers the id.
- **Rendering**: assistant bubbles go through `<MessageContent>` (markdown); user bubbles render plain text with `whitespace-pre-wrap`. A backend `error` frame is thrown by `streamChat` and shown as `⚠ <message>` in the bubble.
- Each rendered `<li>` carries `data-message-id={id}` so `Checkpointer.onJump` can resolve the target via `querySelector` and call `scrollIntoView({ behavior: "smooth", block: "center" })`.
- After a jump, `flashId` briefly highlights the target bubble with `ring-2 ring-[var(--ring)]/60` for 1.2s.
- The scroll area is wrapped in a `relative` parent with the scroller pinned via `absolute inset-0`, so `Checkpointer` can be anchored to the right edge of *just the messages region* (not over the chatbox).
- `Checkpointer` is hidden below `md` to avoid covering the message column on small screens.

## Adding new things — recipes

### New page
- Place it under the right route group: `(auth)` for unauthenticated, `(app)` for inside the shell.
- Server Component by default. If you need state or events, extract a `"use client"` child into a co-located file (e.g. `login-form.tsx` next to `page.tsx`).
- Dynamic segment? Folder name `[id]`, and treat `params` as `Promise<{ id: string }>`.

### New sidebar entry
- Add icon to `components/ui/icons.tsx` if needed.
- Edit `components/shell/sidebar.tsx`. Match the existing collapse-aware pattern:
  ```tsx
  className={cn(
    "flex items-center gap-2 ...",
    collapsed && "md:justify-center md:px-0",
  )}
  ```
  and hide labels under `collapsed && "md:hidden"`. Add a `title` prop so collapsed icons show tooltips.

### Themed surface
- Prefer the design tokens: `bg-[var(--card)]`, `text-[var(--foreground)]`, `border-[var(--border)]`, `text-[var(--muted-foreground)]`. They automatically respond to dark mode via the `.dark` class.
- Use `dark:` utilities only for one-off overrides where a token isn't appropriate.

### New icon
- Add an exported component to `components/ui/icons.tsx` using the existing `base(props)` helper to inherit stroke/viewBox defaults. (e.g. `FolderPlusIcon` = `FolderIcon`'s path + a `M12 10v6M9 13h6` plus.)

### New backend call
- Add it to the matching `lib/api/*` module (or create a new domain module like `uploads.ts`). Use `apiFetch` — never a raw `fetch` — so credentials + 401 handling come for free.
- Pattern: `const res = await apiFetch(path, init); if (!res.ok) throw await parseError(res); return (await res.json()) as T;`. Export typed request/response shapes alongside.
- For JSON bodies set `headers: { "Content-Type": "application/json" }`; for file uploads send a `FormData` body and **omit** the Content-Type (the browser sets the multipart boundary).
- Streaming endpoints follow `chat.ts`: read `res.body`, split SSE frames, and extend `parseFrame` rather than parsing at call sites.

## Commands

```bash
pnpm dev      # next dev (Turbopack)
pnpm build    # next build — also runs strict TS check
pnpm start    # next start (production)
pnpm lint     # eslint
```

Always run `pnpm build` after non-trivial changes — it surfaces TS errors that `pnpm dev` may not.

## Known scope / what's missing

- **Live**: auth (signup/login/logout) and chat (list, history, streaming replies, implicit chat creation) against the FastAPI backend.
- **Still dummy**: **projects** — `lib/projects.ts` `DUMMY_PROJECTS`; "New project" is a no-op button; `/projects` and `/projects/[id]` are stubs.
- **No file upload yet.** Despite being a "document assistant", there's no upload/ingest UI or `lib/api/uploads.ts`. Adding it = a `FormData` POST (skip the JSON `Content-Type`, keep `credentials: "include"`), plus selecting → uploading → processing/indexing → ready states.
- **No client-side route guard.** Protected pages render optimistically; access control relies on the backend `401` → `apiFetch` bounce to `/login`. `localStorage` holds only the theme preference and the cached `auth_user` profile.
- **No tests** yet.
