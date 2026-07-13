# Security & credential handling

## The golden rule
**No credentials, tokens, or secrets in the repository — ever.** Everything sensitive is read
from environment variables (`.env`, which is gitignored) or an OS keychain/secret manager.

## Schwab authentication uses OAuth 2.0 — not a password

A Schwab website username and password **cannot** and **should not** be used to authenticate an
application. The Schwab Trader API flow is:

1. Register a developer app at https://developer.schwab.com.
2. Schwab issues an **App Key** and **App Secret**.
3. The app performs an OAuth 2.0 authorization-code flow; the user logs in **on Schwab's own
   site**, and Schwab returns a short-lived access token + refresh token to your redirect URI.
4. The app stores the refresh token locally (gitignored, ideally OS-encrypted) and exchanges it
   for access tokens as needed.

At no point does the application store or transmit the user's Schwab password.

## Action item: the `Paul.txt` credentials

The kickoff materials included a file containing a Schwab **email and password in plaintext**.
Recommended handling:

- **Do not** place these anywhere in this project.
- **Delete** the plaintext file. If the account password may have been exposed (shared over
  chat/email/unencrypted files), **rotate it** and enable two-factor authentication.
- The only Schwab values this project ever needs are the OAuth **App Key** and **App Secret**
  from the developer portal — put those in `.env`.

## Order entry

`ENABLE_ORDER_ENTRY` defaults to `false`. Even when enabled, order submission must require an
explicit, per-order human confirmation in the UI. Automated/unattended trade execution is out
of scope for the initial build.

## Secrets in CI / deployment
Use the platform's secret store (GitHub Actions secrets, cloud secret manager). Never bake keys
into images or config files.
