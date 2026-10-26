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
| POST | `/auth/prelogin` | `{email}` → `{scheme, kdf_salt, kdf_params}`. Unknown emails get a stable made-up salt. |
| POST | `/auth/register` | `{email, auth_key, …wrapped keys, recovery_wrapped_master_key, recovery_auth_hash}`. The password is never sent: `auth_key` = HKDF(Argon2id(password, salt), "smartspace-auth-v1"). Sets the refresh cookie. |
| POST | `/auth/login` | `{email, auth_key \| password, totp_code?}`. `auth_key` accounts never send the password; staff and older accounts send `password` (older customer accounts also send `auth_key` once and are upgraded). Returns `{mfa_required: true}` when a 2FA code is needed. 8 failed attempts lock the account for 15 minutes. |
| POST | `/auth/google` | `{credential, totp_code?}` – Google ID token. Requires `GOOGLE_CLIENT_ID`, a verified Google email, and refuses to take over unverified password accounts. Returns `oauth_vault_hex` only for Google-created accounts. |
| POST | `/auth/refresh` | Uses the HTTP-only refresh cookie; rotates it. |
| POST | `/auth/logout` | Revokes the current session. |
| GET | `/auth/me` | Current user, plan and quota. |
| POST | `/auth/password` | `{current_auth_key, new_auth_key, new_wrapped_master_key, new_kdf_salt, new_kdf_params}` (staff: `{current_password, new_password}`). Signs out other sessions. |
| POST | `/auth/vault` | One-time vault creation for password accounts without one; also switches the account to `auth_key`. |
| POST | `/auth/recovery-key/confirm` | Marks the recovery key created at sign-up as saved. |
| PUT | `/auth/recovery-key` | `{auth_key, recovery_wrapped_master_key, recovery_auth_hash}` replaces the recovery key. |
| POST | `/auth/password-reset` | `{email}` → emails a single-use link valid for 30 minutes (3 per address per hour). Same response whether or not the account exists. |
| POST | `/auth/password-reset/check` | `{uid, token}` → `{email, has_recovery_key, recovery_wrapped_master_key, has_vault}`. |
| POST | `/auth/password-reset/complete` | `{uid, token, mode: "recovery", recovery_auth, auth_key, wrapped_master_key, kdf_salt, kdf_params}` re-wraps the same vault key; `mode: "reset"` with `confirm_data_loss: true` and new vault keys replaces the vault (old files become unreadable). Signs out every session. |
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
| POST | `/subscription/checkout` | `{plan_code, billing_interval}` → Razorpay order for the plan's price (yearly = monthly × 10; the client never sends an amount). 503 if payments aren't configured. |
| POST | `/subscription/verify` | `{razorpay_order_id, razorpay_payment_id, razorpay_signature}`. The plan comes from the server-side order; each order/payment can be used once. |
| POST | `/subscription/cancel` | Don't renew at period end. |
| GET | `/invoices` | Invoice list. |
| GET | `/invoices/{id}/download` | Printable HTML invoice (IGST or CGST+SGST by state). |
| POST | `/webhooks/razorpay` | Signed with `RAZORPAY_WEBHOOK_SECRET`; unsigned or unconfigured → rejected. `payment.captured` fulfils known orders. |

## Admin (`/admin/`, staff only)
`kpis/`, `pool/`, `users/`, `users/create/`, `users/{id}/upgrade-plan/`, `users/{id}/toggle-status/`,
`users/{id}/validity/`, `users/{id}/purge-data/`, `files/`, `process-lifecycle/`.
