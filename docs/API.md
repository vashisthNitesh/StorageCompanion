# SpeedCloud REST API Specification (`/api/v1/`)

All requests accept and return `application/json` (except presigned binary streams directly to R2).
Access tokens are passed in `Authorization: Bearer <token>`, with rotating refresh tokens managed in `httpOnly` `SameSite=Strict` cookies.

---

## Authentication (`/api/v1/auth/`)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Creates account, saves KEK salt, params, public key, and wrapped Master Key. |
| `POST` | `/api/v1/auth/login` | Validates credentials & TOTP; returns access token and wrapped keys; sets refresh cookie. |
| `POST` | `/api/v1/auth/refresh` | Rotates refresh token from cookie and returns fresh access token. |
| `POST` | `/api/v1/auth/logout` | Blacklists refresh token and clears cookie. |
| `GET` | `/api/v1/auth/me` | Current user profile, active subscription status, and storage quota. |
| `POST` | `/api/v1/auth/password` | Re-wraps Master Key with new KEK and updates password. |
| `POST` | `/api/v1/auth/mfa/enroll` | Generates TOTP secret and QR code base64. |
| `POST` | `/api/v1/auth/mfa/verify` | Confirms code and activates 2FA. |
| `POST` | `/api/v1/auth/mfa/disable` | Disables 2FA with password check. |
| `GET` | `/api/v1/auth/sessions` | Lists active sessions. |
| `DELETE` | `/api/v1/auth/sessions/{id}` | Revokes session. |

---

## Storage & Nodes (`/api/v1/`)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/nodes?parent={uuid}` | Cursor-paginated listing of files and folders in directory. |
| `POST` | `/api/v1/nodes` | Creates a new folder with encrypted name and nonce. |
| `GET` | `/api/v1/nodes/{id}` | Returns node metadata. |
| `PATCH` | `/api/v1/nodes/{id}` | Renames or moves a node. |
| `DELETE` | `/api/v1/nodes/{id}` | Moves node to trash. |
| `POST` | `/api/v1/nodes/{id}/restore` | Restores node from trash. |
| `GET` | `/api/v1/nodes/{id}/versions` | Lists historical file versions. |
| `GET` | `/api/v1/nodes/{id}/download` | Issues presigned GET URL (TTL ≤ 15 min) + wrapped File Key. |
| `POST` | `/api/v1/uploads` | Initializes direct-to-R2 multipart upload; returns presigned PUT URLs per chunk. |
| `POST` | `/api/v1/uploads/{id}/complete` | Commits multipart upload, records FileVersion, and increments quota atomically. |
| `DELETE` | `/api/v1/uploads/{id}` | Aborts upload session. |
| `GET` | `/api/v1/quota` | Current storage consumption, limit, and percent used. |

---

## Sharing (`/api/v1/`)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/shares` | Creates public link or user-to-user share. |
| `GET` | `/api/v1/shares` | Lists created and received shares. |
| `DELETE` | `/api/v1/shares/{id}` | Revokes a share. |
| `GET` | `/api/v1/public/shares/{token}` | Unauthenticated metadata for public share link. |
| `POST` | `/api/v1/public/shares/{token}/auth` | Verifies link password (rate limited 10/hr). |
| `GET` | `/api/v1/public/shares/{token}/download` | Generates presigned GET download URL for public recipient. |

---

## Billing (`/api/v1/`)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/plans` | Lists available subscription plans (No Free Tier). |
| `GET` | `/api/v1/subscription` | Current user's subscription details. |
| `POST` | `/api/v1/subscription/checkout` | Creates a Razorpay order / subscription session. |
| `POST` | `/api/v1/subscription/verify` | Verifies Razorpay payment signature & activates plan. |
| `POST` | `/api/v1/subscription/cancel` | Flags subscription for cancellation at period end. |
| `GET` | `/api/v1/invoices` | Past payment invoice history. |
| `POST` | `/api/v1/webhooks/razorpay` | Idempotent webhook handler with HMAC-SHA256 signature verification. |
