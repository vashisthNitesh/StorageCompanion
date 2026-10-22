# UI audit — SmartSpace frontend

Audit of `frontend/src` taken before the UI revamp (branch `ui-revamp`, base commit `a27c153`).
Every item is a checklist entry; `[x]` means resolved in the revamp. Sections 11–12 are for the product owner and the backend and stay open.

**Stack:** Vue 3.5 (`<script setup>`, TypeScript), Pinia 2, Vue Router 4, Tailwind 3.4, Vite 5,
Lucide icons. API client: `src/lib/api/index.ts` (`apiRequest` / `apiFetch`, refresh-on-401,
30 s header timeout, throws `ApiError {status, data}`). Notifications: hand-rolled
`src/stores/toast.ts` + `components/ToastHost.vue`. Confirmations: `components/ConfirmDialog.vue`.

## 1. Native browser dialogs
- [ ] No `alert(` / `confirm(` / `prompt(` calls remain in `src` (removed in the previous pass; the
      only hit is the method name `confirm()` in `components/ConfirmDialog.vue:21`). Guarded by an
      ESLint `no-alert` rule from now on.

## 2. Raw server output rendered in the UI
Every one of these renders `err.message` directly, which is whatever text the server sent
(`ApiError` uses `data.error || data.message || data.detail`), so Django/DRF wording such as
"email: Enter a valid email address." or "Request failed (413)." can reach the user.
- [ ] `features/settings/SettingsView.vue:45, 68, 83, 100, 153`
- [ ] `features/auth/LoginView.vue:41`
- [ ] `features/auth/RegisterView.vue:43, 60`
- [ ] `features/auth/GoogleSignInButton.vue:34`
- [ ] `features/admin/AdminUsers.vue:55, 112, 148`
- [ ] `features/admin/AdminFiles.vue:40`
- [ ] `features/admin/AdminOverview.vue:25, 41`
- [ ] `features/files/MoveDialog.vue:27, 43`
- [ ] `features/files/NameDialog.vue:54`
- [ ] `features/files/VersionsDialog.vue:27`
- [ ] `features/files/FileManager.vue:125`
- [ ] `features/files/TrashView.vue:30, 43`
- [ ] `features/files/useFileDownload.ts:128`
- [ ] `features/billing/BillingView.vue:68, 84`
- [ ] `stores/billing.ts:82`, `stores/files.ts:90, 154`, `stores/upload.ts:246`
- [ ] `layouts/AppLayout.vue:151`
- [ ] `components/ConfirmDialog.vue:29`
- [ ] `lib/api/index.ts:135` — builds the message from raw response fields; replaced by
      `normalizeApiError()` (`src/lib/errors.ts`) which maps status/code to fixed copy and only
      passes through field errors to the matching inputs.
- [ ] No `v-html`, `dangerouslySetInnerHTML` or `JSON.stringify` rendered into templates (none found).

## 3. Browser validation bubbles
All forms rely on native `required` / `minlength` / `type="email"` (25 attributes) and none has `novalidate`:
- [ ] `features/auth/LoginView.vue:91, 123`
- [ ] `features/auth/RegisterView.vue:74, 89`
- [ ] `features/settings/SettingsView.vue:208, 272, 327`
- [ ] `features/files/NameDialog.vue:63`
- [ ] `features/admin/AdminUsers.vue:257, 286, 321`
- [ ] `layouts/AppLayout.vue:355`

## 4. Native `<select>`
- [ ] `features/files/FileManager.vue:228` (type filter), `:232` (sort)
- [ ] `features/billing/BillingView.vue:158` (GST state, 36 options — needs search)
- [ ] `features/admin/AdminUsers.vue:178, 182, 261, 267, 338, 345`
- [ ] `features/admin/AdminFiles.vue:69, 74`

## 5. Native `title=` used as tooltips
- [ ] `features/files/FileManager.vue:212, 215, 218, 243, 252`
- [ ] `features/files/FileListView.vue:68, 74, 84`
- [ ] `features/files/FileGridView.vue:48, 56`
- [ ] `features/files/FileName.vue:17`
- [ ] `features/files/UploadTray.vue:56, 69, 72, 75, 78`
- [ ] `features/files/TrashView.vue:108`
- [ ] `features/files/VersionsDialog.vue:37`
- [ ] `features/settings/SettingsView.vue:321`
- [ ] `features/auth/PasswordInput.vue:26`, `features/auth/GoogleSignInButton.vue:56`
- [ ] `features/admin/AdminOverview.vue:88, 89`
- [ ] `layouts/AppLayout.vue:215, 262`
(`title=` props on `AuthShell`, `BaseModal`, `ConfirmDialog` are component props, not tooltips.)

## 6. Unstyled checkboxes / radios
- [ ] `features/auth/RegisterView.vue:113` (native checkbox)
- [ ] `features/files/MoveDialog.vue:64` (visually hidden radio list → folder tree picker)

## 7. `console.*`
- [ ] None in `src` (the only hit, `router/index.ts:53`, is a comment). Production builds now drop
      `console`/`debugger` via esbuild, and `src/lib/logger.ts` is silent in production.

## 8. Loading states and layout shift
- [ ] Spinners in empty space: `FileManager.vue` (vault locked, search), `TrashView.vue`,
      `MoveDialog.vue`, `VersionsDialog.vue`, `AdminUsers.vue`, `AdminFiles.vue`, `AppLayout.vue`
      (opening vault). Replaced with skeletons of the final layout.

## 9. Design-system gaps
- [ ] Colours hard-coded as Tailwind `slate-*` / `brand-*` in every file; no semantic tokens, no dark mode.
- [ ] Fonts loaded from Google Fonts at runtime (`index.html`) — now self-hosted variable Inter.
- [ ] Hand-rolled modal (`BaseModal.vue`) without focus trap; hand-rolled menu (`ItemMenu.vue`);
      no tooltip, select, combobox, checkbox, switch, segmented control or drawer components.
- [ ] No `lint` setup although `package.json` has a `lint` script (ESLint not installed).
- [ ] No error boundary, no 404 page (unknown routes redirect to `/`), no offline banner, no
      keyboard shortcuts, no multi-select or bulk actions, no undo.

## 10. App-shell findings from screenshots
- [ ] Security nav item can show the browser focus outline instead of the active style.
- [ ] No-plan state: full-width blue banner on every page plus three more "See plans" buttons.
- [ ] Upload buttons remain enabled without a plan and silently navigate to billing.

## 11. Product copy that contradicts behaviour (for the product owner)
These come from the plan data seeded by `backend/apps/billing/management/commands/seed_plans.py`.
The UI no longer shows the seeded `features` strings; it builds comparable lists from the plan
fields (storage, max file size, version history) plus what every plan really gets.
- [ ] "Two-Factor Authentication" is listed only on Super Pack, but the Security page offers 2FA to
      every account.
- [ ] "Zero Egress Bandwidth Fees" (Entry/Smart) vs "Zero Bandwidth Limits" (Value) describe the same
      thing differently; every plan has unmetered downloads.
- [ ] "Client-Side Decrypted Search" is listed only on Smart Pack; search works the same on every plan.
- [ ] "Extended 90-Day File Version History" / "Full 365-Day Versioning Retention": the backend never
      deletes old versions, so `version_retention_days` is not enforced.
- [ ] "Priority Direct WhatsApp & Email Support" (Super Pack): there is no support channel in the product.
- [ ] Switching to a different plan starts a new period today; remaining time on the old plan is
      **not** carried over or refunded (`billing/services.py: activate_subscription`). The UI now says
      so before checkout — confirm this is the intended policy.

## 12. Spec items the backend cannot support yet (see "Backend follow-ups" in the final summary)
- [ ] Starred items, Shared items, Copy link — not supported (sharing was removed); omitted from the UI.
- [ ] 409 duplicate-name errors — the API allows duplicates; duplicates are detected in the browser
      before upload/create/rename instead.
- [ ] Trash retention ("Deletes permanently in N days") — trash is never purged automatically; not shown.
- [ ] Forgot / reset password and email verification — no endpoints. Password vaults can't be reset by
      design, so the "Forgot password" page explains this instead of sending a reset link.
- [ ] Regenerate 2FA recovery codes — no endpoint (re-enrolling would disable 2FA); not offered.
- [ ] CGST/SGST vs IGST preview at checkout — the seller's state code isn't exposed to the frontend, so
      the summary shows "GST (18%) included" and the invoice shows the split.
- [ ] Invoice PDF — the API returns a printable HTML invoice; the button downloads that.
- [ ] Thumbnails — files are end-to-end encrypted and preview was removed by request; grid uses type tiles.
- [ ] Device location — only the IP address is stored.
- [ ] Payment status other than Paid (Failed / Refunded) — invoices are only created for paid orders.
