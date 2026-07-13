# Schwab API — what Paul needs to provide, and how to get it

The app authenticates to Schwab with **OAuth 2.0**. Paul never gives anyone his Schwab
password. Instead he registers a developer "app" on Schwab's portal, which issues two values:

- **App Key** (a.k.a. Client ID / Consumer Key)
- **App Secret** (Client Secret)

Those two values — plus a one-time login authorization — are all the project needs.

---

## What to send me (the short version)

1. **App Key**
2. **App Secret**
3. Confirmation of the **Callback URL** he registered (must match ours exactly — see step 5)
4. Confirmation the app status is **"Ready for Use"** (approved)

> Send the App Key/Secret through something private (a password manager share or secure note),
> **not** plaintext email or chat. And again: **do not send the Schwab account password** — the
> API doesn't use it.

---

## Step-by-step for Paul

1. **Go to** https://developer.schwab.com and click **Register** / create a developer account.
   (He signs in / links using his existing Schwab credentials on Schwab's own site.)

2. **Confirm the brokerage account is API-eligible.** Standard individual Schwab brokerage
   accounts qualify. If in doubt, Schwab developer support can confirm.

3. **Create an app:** Dashboard → **"Apps"** → **"Add a new app"** (a.k.a. Register an App).
   Give it a name (e.g. "M&P Trading Terminal") and description.

4. **Select the API product:** **Trader API - Individual**. (Schwab's individual tier bundles
   market data *and* accounts/trading into this one product — you do not need to pick two
   separate products. Confirm under the **Subscriptions** tab that it shows **Approved**.)

5. **Set the Callback URL (redirect URI).** This must match what our app uses exactly.
   - For initial development he can enter: `https://127.0.0.1:8182/callback`
   - For the live site it will be: `https://<our-domain>/schwab/callback`
   - He can add/update this later once we lock the domain, so a placeholder is fine to start.

6. **Submit for approval.** The app status starts as pending. Schwab reviews it — this can take
   **a few days**. When it flips to **"Ready for Use"**, the API is live.

7. **Copy the App Key and App Secret** from the app's page and send them to me (privately).

8. **One-time authorization:** when I wire it up, Paul (as the account owner) does a single
   Schwab login through the app to grant access. The app stores a refresh token — never his
   password.

---

## Things to know up front

- **Approval takes time.** Budget a few days between Paul submitting the app and it being usable.
- **Token refresh:** Schwab access tokens last ~30 minutes; the refresh token lasts ~7 days,
  after which the account owner must re-authorize. The app handles refresh automatically within
  that window, but expect a periodic re-login. (This is a known Schwab API constraint.)
- **Market-data entitlements** are tied to Paul's account. Real-time vs. delayed quotes depend
  on his account's data agreements.
- **One shared account:** because all data comes from Paul's Schwab account, that account is the
  single source for the whole app. Fine for a small internal tool; see DEPLOYMENT.md for the
  multi-user implications.
