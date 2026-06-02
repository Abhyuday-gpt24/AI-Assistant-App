# Deploying behind Nginx + HTTPS (EC2)

This sets up Nginx as a **reverse proxy** that serves both the frontend and the
backend under a **single HTTPS origin**:

```
                          ┌──────────────────────────────┐
   Browser  ──HTTPS──►    │  Nginx  (ports 80, 443)       │
                          │                               │
                          │   /          → frontend :3000 │
                          │   /api/...   → backend  :8000 │
                          └──────────────────────────────┘
```

Why this is better than exposing :3000 and :8000 directly:

- **One origin** (`https://your-domain`) for everything → frontend and backend
  are same-origin, so **CORS is no longer needed** and cookies work normally.
- **HTTPS / secure context** → `crypto.randomUUID`, `Secure` cookies, and other
  browser secure-context APIs all work. You can turn `COOKIE_SECURE` back to
  `true` and drop the `allowedDevOrigins` / dev-mode workarounds.
- Only ports **80** and **443** are exposed publicly; 3000 and 8000 stay bound to
  localhost on the instance.

---

## 0. Prerequisites

1. **A domain name** (e.g. `app.example.com`). Let's Encrypt cannot issue certs
   for a bare IP. If you don't own one, a free option is a subdomain from
   DuckDNS / No-IP, or buy one cheaply. (No domain at all? See the self-signed
   fallback at the bottom — works, but browsers show a warning.)

2. **DNS A record** pointing the domain at your EC2 **public IP**:
   ```
   app.example.com.   A   100.48.47.97
   ```
   Verify it resolves before continuing:
   ```bash
   dig +short app.example.com      # should print 100.48.47.97
   ```

3. **EC2 Security Group inbound rules** — open:
   - TCP **80**  (HTTP, needed for the Let's Encrypt challenge + redirect)
   - TCP **443** (HTTPS)

   You can now **remove** the public 3000 and 8000 rules — Nginx reaches them
   locally.

---

## 1. Install Nginx + Certbot

(Ubuntu / Debian on EC2; for Amazon Linux use `sudo dnf install nginx` and the
certbot instructions for RHEL.)

```bash
sudo apt update
sudo apt install -y nginx
sudo snap install --classic certbot
sudo ln -sf /snap/bin/certbot /usr/bin/certbot
```

---

## 2. Nginx reverse-proxy config

Create `/etc/nginx/sites-available/ai-assistant`:

```nginx
server {
    listen 80;
    server_name app.example.com;          # <-- your domain

    # Backend API → FastAPI on :8000
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Streaming / SSE (chat responses): don't buffer, keep the connection open
        proxy_buffering off;
        proxy_read_timeout 3600s;
    }

    # Everything else → Next.js on :3000
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket upgrade (Next.js HMR in dev; harmless in prod)
        proxy_set_header Upgrade    $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    client_max_body_size 50M;   # allow file uploads (tune to your needs)
}
```

Enable it and reload:

```bash
sudo ln -s /etc/nginx/sites-available/ai-assistant /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default     # drop the welcome page
sudo nginx -t                                   # test config
sudo systemctl reload nginx
```

At this point `http://app.example.com` should load the app (over HTTP).

---

## 3. Get the HTTPS certificate

Certbot will obtain the cert AND rewrite the Nginx config to serve HTTPS +
redirect HTTP→HTTPS automatically:

```bash
sudo certbot --nginx -d app.example.com
```

Answer the prompts (email, agree to ToS). When it asks about redirecting HTTP to
HTTPS, choose **redirect**. Done — `https://app.example.com` now works.

**Auto-renewal** is installed automatically. Verify with:

```bash
sudo certbot renew --dry-run
```

---

## 4. Update the app config for the single HTTPS origin

### Frontend `.env` (AI-Assistant-Frontend/.env)

Point the API base at the same HTTPS origin (Nginx routes `/api` to the backend):

```
NEXT_PUBLIC_API_BASE_URL=https://app.example.com
```

Then rebuild (NEXT_PUBLIC_* is baked in at build time) and run in **production**:

```bash
cd AI-Assistant-Frontend
npm run build
npm run start -- -H 127.0.0.1 -p 3000
```

> Bind to `127.0.0.1` now, not `0.0.0.0` — only Nginx needs to reach it.
> In production mode you no longer need `allowedDevOrigins` in `next.config.ts`
> (it only affects `next dev`); leaving it is harmless.

### Backend

1. `.env` → turn `Secure` cookies back on (you're on HTTPS now):
   ```
   COOKIE_SECURE=true
   ```

2. CORS: since the browser now talks only to `https://app.example.com` and the
   API is same-origin, CORS is effectively unused. Update the allow-list to the
   HTTPS origin (keep localhost for local dev):
   ```python
   allow_origins=[
       "http://localhost:3000",
       "https://app.example.com",
   ],
   ```

3. Run the backend bound to localhost:
   ```bash
   cd AI-Assistant-Backend
   uvicorn app:app --host 127.0.0.1 --port 8000
   ```

---

## 5. Keep the processes alive (recommended)

Right now your `uvicorn` and `npm start` die when you close the SSH session. Use
a process manager so they survive reboots/disconnects.

**Backend — systemd** (`/etc/systemd/system/ai-backend.service`):

```ini
[Unit]
Description=AI Assistant Backend
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/AI-Assistant-App/AI-Assistant-Backend
ExecStart=/home/ubuntu/AI-Assistant-App/AI-Assistant-Backend/.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ai-backend
```

**Frontend — same pattern** (`ai-frontend.service`), with
`ExecStart=/usr/bin/npm run start -- -H 127.0.0.1 -p 3000` and the frontend
`WorkingDirectory`. (Or use `pm2` if you prefer.)

---

## 6. Verify end-to-end

1. Open `https://app.example.com` — padlock should show, no cert warning.
2. F12 → Network → log in. The request goes to
   `https://app.example.com/api/auth/login` → **200**.
3. Application → Cookies: `access_token` present with **`Secure`** + `HttpOnly`.
4. `GET /api/chats` → **200**. Login persists across refreshes.
5. No `crypto.randomUUID` error (you're in a secure context now).

---

## No domain: self-signed HTTPS on the raw IP (full walkthrough)

Use this when you have no domain. The browser will show a one-time "Not secure"
warning (the cert isn't from a trusted CA), but once you click through, the page
runs over TLS and the browser treats it as a **secure context** — so `Secure`
cookies, `crypto.randomUUID`, etc. all work. Let's Encrypt is **not** possible
without a domain, so this is the only HTTPS option for a bare IP.

This section is self-contained: it does **not** use Certbot (steps 3 above). Do
steps 0–2 first (security group, install Nginx, but you can **skip Certbot**),
then follow the steps below instead of step 3.

### A. Generate a self-signed cert WITH an IP SAN

> Critical: the IP must be in the cert's **Subject Alternative Name**. A cert
> with only `CN=100.48.47.97` is rejected by Chrome with
> `NET::ERR_CERT_COMMON_NAME_INVALID` and sometimes no way to proceed. The
> `-addext` below adds the SAN.

```bash
sudo mkdir -p /etc/nginx/ssl
sudo openssl req -x509 -nodes -days 825 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/selfsigned.key \
  -out    /etc/nginx/ssl/selfsigned.crt \
  -subj "/CN=100.48.47.97" \
  -addext "subjectAltName=IP:100.48.47.97"
```

(`-days 825` is the max most browsers accept. Regenerate before it expires.)

### B. Nginx config (replaces the step-2 `server` block)

Create `/etc/nginx/sites-available/ai-assistant` with **two** server blocks —
one redirects HTTP→HTTPS, one serves HTTPS:

```nginx
# Redirect all plain HTTP to HTTPS
server {
    listen 80;
    server_name 100.48.47.97;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name 100.48.47.97;

    ssl_certificate     /etc/nginx/ssl/selfsigned.crt;
    ssl_certificate_key /etc/nginx/ssl/selfsigned.key;

    # Backend API → FastAPI on :8000
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Streaming / SSE (chat responses)
        proxy_buffering off;
        proxy_read_timeout 3600s;
    }

    # Everything else → Next.js on :3000
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade           $http_upgrade;
        proxy_set_header Connection        "upgrade";
    }

    client_max_body_size 50M;
}
```

Enable and reload:

```bash
sudo ln -s /etc/nginx/sites-available/ai-assistant /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### C. Update the app config (single HTTPS origin, no port)

With Nginx on 443, the origin is `https://100.48.47.97` (no `:3000`/`:8000`).

**Frontend `.env`** — then rebuild (NEXT_PUBLIC is baked in at build time):
```
NEXT_PUBLIC_API_BASE_URL=https://100.48.47.97
```
```bash
cd AI-Assistant-Frontend
npm run build
npm run start -- -H 127.0.0.1 -p 3000
```

**Backend `.env`** — secure cookies work again over HTTPS:
```
COOKIE_SECURE=true
```

**Backend CORS** (app.py) — same-origin now, but set the allow-list to the
HTTPS origin (note: no port, and `https`):
```python
allow_origins=[
    "http://localhost:3000",
    "https://100.48.47.97",
],
```
```bash
cd AI-Assistant-Backend
uvicorn app:app --host 127.0.0.1 --port 8000
```

### D. Open it

1. Browse to **`https://100.48.47.97`** (https, no port).
2. You'll see the warning → click **Advanced → Proceed to 100.48.47.97
   (unsafe)**. You only do this **once per browser/device**.
3. From here it's a secure context: log in → `access_token` cookie stored with
   `Secure`, `GET /api/chats` → 200, no `randomUUID` error.

### Gotchas specific to self-signed

- **Every device/browser** that uses the app must accept the warning once. Fine
  for you/testers; not acceptable for real end users — that's what a real domain
  + Let's Encrypt is for.
- If you later get a domain, just do the step-3 Certbot flow and swap the
  `server_name` + `NEXT_PUBLIC_API_BASE_URL` + CORS origin to the domain. The
  trusted cert removes the warning entirely.
- `825` days is roughly the cert lifetime ceiling browsers honor; set a reminder
  to regenerate (step A) before it expires.
