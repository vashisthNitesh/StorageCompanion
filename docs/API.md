# SmartSpace REST API (`/api/v1/`)

All endpoints return JSON. Authenticated endpoints need `Authorization: Bearer <access_token>`;
tokens in the URL are not accepted. Access tokens last 30 minutes and are bound to a session
(`sid` claim); revoking the session invalidates them immediately. Errors look like
`{"success": false, "error": "<message>", "details": {...}, "status_code": 400}`.

## Health
| Method | Path | Notes |
|---|---|---|
| GET | `/health` | Liveness probe (no auth, no throttling) |

## Authentication (`/auth/`)
| Method | Path | Notes |
|---|---|---|
| GET | `/auth/config` | `{google_client_id, payments_enabled}` |
| POST | `/auth/register` | Email, password and client-generated wrapped keys. Sets the refresh cookie. |
| POST | `/auth/login` | `{email, password, totp_code?}`. Returns `{mfa_required: true}` when a 2FA code is needed. 8 failed attempts lock the account for 15 minutes. |
| POST | `/auth/google` | `{credential, totp_code?}` – Google ID token. Requires `GOOGLE_CLIENT_ID`, a verified Google email, and refuses to take over unverified password accounts. Returns `oauth_vault_hex` only for Google-created accounts. |
| POST | `/auth/refresh` | Uses the HTTP-only refresh cookie; rotates it. |
| POST | `/auth/logout` | Revokes the current session. |
| GET | `/auth/me` | Current user, plan and quota. |
| POST | `/auth/password` | Change password (and re-wrapped master key). Signs out other sessions. |
| POST | `/auth/vault` | One-time vault creation for password accounts without one. |
| GET | `/auth/vault/google-key` | Vault key for Google-created accounts (new browser tabs). |
| POST | `/auth/mfa/enroll` · `/auth/mfa/verify` · `/auth/mfa/disable` | TOTP two-step verification. |
| GET | `/auth/sessions` | Active sessions with `is_current`. |
| DELETE | `/auth/sessions/{id}` | Sign a device out immediately. |

Login, Google sign-in, registration, MFA and password changes share a 10/minute per-client limit.

## Files (`/nodes`, `/uploads`)
| Method | Path | Notes |
|---|---|---|
| GET | `/nodes?parent=<id>` | Folder contents (root when omitted). Not paginated. |
| GET | `/nodes?all=true` | Every non-trashed item (used for client-side search). |
| GET | `/nodes?trashed=true` | Top-level trashed items. |
| POST | `/nodes` | Create folder `{parent, encrypted_name, name_nonce}`. |
| PATCH | `/nodes/{id}` | Rename and/or move (moves into own subfolders are refused). |
| DELETE | `/nodes/{id}` | Move to trash; `?permanent=true` (or already trashed) deletes forever. |
| POST | `/nodes/{id}/restore` | Restore from trash. |
| GET | `/nodes/{id}/versions` | Version list. |
| GET | `/nodes/{id}/download[?v=n]` | Wrapped file key, nonce, part size and stream URL. |
| GET | `/nodes/{id}/content[?v=n]` | Encrypted byte stream (owner only, Range supported). |
| POST | `/uploads` | Start upload `{parent_id?, node_id?, encrypted_name, name_nonce, size_bytes}` → `{upload_session_id, part_size, total_parts}`. `node_id` uploads a new version. |
| POST | `/uploads/{id}/parts/{n}` | Raw encrypted part (`application/octet-stream`), exactly `part_size + 16` bytes except the last. |
| POST | `/uploads/{id}/complete` | `{wrapped_file_key, content_nonce}`. Idempotent. |
| DELETE | `/uploads/{id}` | Abort. |
| GET | `/quota` | Storage usage and upload eligibility. |

## Billing
| Method | Path | Notes |
|---|---|---|
| GET | `/plans` | Public plan list. |
| GET | `/subscription` | Current subscription. |
| POST | `/subscription/checkout` | `{plan_code, billing_interval, billing_state}` → Razorpay order. 503 if payments aren't configured. |
| POST | `/subscription/verify` | `{razorpay_order_id, razorpay_payment_id, razorpay_signature}`. The plan comes from the server-side order; each order/payment can be used once. |
| POST | `/subscription/cancel` | Don't renew at period end. |
| GET | `/invoices` | Invoice list. |
| GET | `/invoices/{id}/download` | Printable HTML invoice (IGST or CGST+SGST by state). |
| POST | `/webhooks/razorpay` | Signed with `RAZORPAY_WEBHOOK_SECRET`; unsigned or unconfigured → rejected. `payment.captured` fulfils known orders. |

## Admin (`/admin/`, staff only)
`kpis/`, `pool/`, `users/`, `users/create/`, `users/{id}/upgrade-plan/`, `users/{id}/toggle-status/`,
`users/{id}/validity/`, `users/{id}/purge-data/`, `files/`, `process-lifecycle/`.
