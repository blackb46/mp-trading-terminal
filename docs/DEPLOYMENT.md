# Deployment

**Decision: the app is hosted on a website (multi-user, publicly reachable), not run locally.**

This affects auth, cost, data-provider licensing, and the Schwab OAuth flow. Notes below.

## Topology

```
   Browser (users)
        │  HTTPS + WSS
        ▼
   ┌─────────────────────┐        ┌──────────────────────┐
   │  Frontend (static)  │        │   Backend (FastAPI)  │
   │  React build on a   │──API──▶│   on a container host │
   │  CDN / static host  │        │   (always-on service) │
   └─────────────────────┘        └───────────┬──────────┘
                                              │
                              ┌───────────────┼───────────────┐
                              ▼               ▼               ▼
                        Market data       Redis cache      Database
                        WebSocket         (quotes, scan    (users, watchlists,
                        (server-side)      results)         audit log)
```

Key point: the **market-data WebSocket connection lives on the server**, not in each user's
browser. One server-side feed fans out scan results to all connected browsers over our own
WebSocket. This is required for cost (one data subscription, not one per user) and for keeping
provider API keys off the client.

## Hosting options (pick one)

| Piece            | Good fit                                              |
|------------------|------------------------------------------------------|
| Frontend (static)| Vercel, Netlify, Cloudflare Pages, S3+CloudFront     |
| Backend (always-on, WebSocket) | Render, Railway, Fly.io, AWS ECS/Fargate, a VPS |
| Cache            | Managed Redis (Upstash, Redis Cloud) or self-hosted  |
| Database         | Managed Postgres (Neon, Supabase, RDS)               |

> Note: the backend must be an **always-on** service (it holds the live market-data socket and
> runs the scan loop). Pure serverless/lambda is a poor fit for the streaming core.

## What hosting adds vs. a local app

1. **User accounts & auth** — a public site needs login, sessions, and per-user data
   (watchlists, preferences). Add an auth provider (e.g. Auth0/Clerk/Supabase Auth) or roll
   email+password with proper hashing. *(New work item — see roadmap Phase 2.5.)*
2. **HTTPS everywhere** — required for secure WebSockets (WSS) and for Schwab's OAuth redirect.
3. **Schwab OAuth redirect URI** must be a real HTTPS URL registered with the Schwab app
   (e.g. `https://app.example.com/schwab/callback`), not `127.0.0.1`.
4. **Data-provider licensing** — redistributing market data to multiple end users can require a
   different (more expensive) license tier than personal use. **Confirm with the provider.**
5. **Per-user vs. shared brokerage** — does every user connect *their own* Schwab account, or
   is there one shared account? Multi-user brokerage = each user runs their own OAuth flow and
   we store their tokens encrypted, per user. This is a significant design fork — see below.
6. **Cost scales with users** — server, cache, DB, bandwidth, and possibly data licensing.
7. **Secrets management** — use the host's secret store; never in the repo or the client bundle.

## Open sub-decisions created by "hosted"
- Who can access the site — Paul only, a small team, or the public? (Drives auth strictness and
  data-licensing exposure.)
- One shared Schwab account, or each user links their own?
- Custom domain?
