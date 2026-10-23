# UI audit — SmartSpace frontend

Audit of `frontend/src` taken before the UI revamp (branch `ui-revamp`, base commit `a27c153`).
Every item is a checklist entry; `[x]` means resolved in the revamp. Sections 11–12 are for the product owner and the backend and stay open.

**Stack:** Vue 3.5 (`<script setup>`, TypeScript), Pinia 2, Vue Router 4, Tailwind 3.4, Vite 5,
Lucide icons. API client: `src/lib/api/index.ts` (`apiRequest` / `apiFetch`, refresh-on-401,
30 s header timeout, throws `ApiError {status, data}`). Notifications: hand-rolled
`src/stores/toast.ts` + `components/ToastHost.vue`. Confirmations: `components/ConfirmDialog.vue`.

## 1. Native browser dialogs
- [x] No `alert(` / `confirm(` / `prompt(` calls remain in `src` (removed in the previous pass; the
      only hit is the method name `confirm()` in `components/ConfirmDialog.vue:21`). Guarded by an
      ESLint `no-alert` rule from now on.

## 2. Raw server output rendered in the UI
Every one of these renders `err.message` directly, which is whatever text the server sent
(`ApiError` uses `data.error || data.message || data.detail`), so Django/DRF wording such as
"email: Enter a valid email address." or "Request failed (413)." can reach the user.
- [x] `features/settings/SettingsView.vue:45, 68, 83, 100, 153`
- [x] `features/auth/LoginView.vue:41`
- [x] `features/auth/RegisterView.vue:43, 60`
- [x] `features/auth/GoogleSignInButton.vue:34`
- [x] `features/admin/AdminUsers.vue:55, 112, 148`
- [x] `features/admin/AdminFiles.vue:40`
- [x] `features/admin/AdminOverview.vue:25, 41`
- [x] `features/files/MoveDialog.vue:27, 43`
- [x] `features/files/NameDialog.vue:54`
- [x] `features/files/VersionsDialog.vue:27`
- [x] `features/files/FileManager.vue:125`
- [x] `features/files/TrashView.vue:30, 43`
- [x] `features/files/useFileDownload.ts:128`
- [x] `features/billing/BillingView.vue:68, 84`
- [x] `stores/billing.ts:82`, `stores/files.ts:90, 154`, `stores/upload.ts:246`
- [x] `layouts/AppLayout.vue:151`
- [x] `components/ConfirmDialog.vue:29`
- [x] `lib/api/index.ts:135` — builds the message from raw response fields; replaced by
      `normalizeApiError()` (`src/lib/errors.ts`) which maps status/code to fixed copy and only
      passes through field errors to the matching inputs.
- [x] No `v-html`, `dangerouslySetInnerHTML` or `JSON.stringify` rendered into templates (none found).

## 3. Browser validation bubbles
All forms rely on native `required` / `minlength` / `type="email"` (25 attributes) and none has `novalidate`:
- [x] `features/auth/LoginView.vue:91, 123`
- [x] `features/auth/RegisterView.vue:74, 89`
- [x] `features/settings/SettingsView.vue:208, 272, 327`
- [x] `features/files/NameDialog.vue:63`
- [x] `features/admin/AdminUsers.vue:257, 286, 321`
- [x] `layouts/AppLayout.vue:355`

## 4. Native `<select>`
- [x] `features/files/FileManager.vue:228` (type filter), `:232` (sort)
- [x] `features/billing/BillingView.vue:158` (GST state, 36 options — needs search)
- [x] `features/admin/AdminUsers.vue:178, 182, 261, 267, 338, 345`
- [x] `features/admin/AdminFiles.vue:69, 74`

## 5. Native `title=` used as tooltips
- [x] `features/files/FileManager.vue:212, 215, 218, 243, 252`
- [x] `features/files/FileListView.vue:68, 74, 84`
- [x] `features/files/FileGridView.vue:48, 56`
- [x] `features/files/FileName.vue:17`
- [x] `features/files/UploadTray.vue:56, 69, 72, 75, 78`
- [x] `features/files/TrashView.vue:108`
- [x] `features/files/VersionsDialog.vue:37`
- [x] `features/settings/SettingsView.vue:321`
- [x] `features/auth/PasswordInput.vue:26`, `features/auth/GoogleSignInButton.vue:56`
- [x] `features/admin/AdminOverview.vue:88, 89`
- [x] `layouts/AppLayout.vue:215, 262`
(`title=` props on `AuthShell`, `BaseModal`, `ConfirmDialog` are component props, not tooltips.)

## 6. Unstyled checkboxes / radios
- [x] `features/auth/RegisterView.vue:113` (native checkbox)
- [x] `features/files/MoveDialog.vue:64` (visually hidden radio list → folder tree picker)

## 7. `console.*`
- [x] None in `src` (the only hit, `router/index.ts:53`, is a comment). Production builds now drop
      `console`/`debugger` via esbuild, and `src/lib/logger.ts` is silent in production.

## 8. Loading states and layout shift
- [x] Spinners in empty space: `FileManager.vue` (vault locked, search), `TrashView.vue`,
      `MoveDialog.vue`, `VersionsDialog.vue`, `AdminUsers.vue`, `AdminFiles.vue`, `AppLayout.vue`
      (opening vault). Replaced with skeletons of the final layout.

## 9. Design-system gaps
- [x] Colours hard-coded as Tailwind `slate-*` / `brand-*` in every file; no semantic tokens, no dark mode.
- [x] Fonts loaded from Google Fonts at runtime (`index.html`) — now self-hosted variable Inter.
- [x] Hand-rolled modal (`BaseModal.vue`) without focus trap; hand-rolled menu (`ItemMenu.vue`);
      no tooltip, select, combobox, checkbox, switch, segmented control or drawer components.
- [x] No `lint` setup although `package.json` has a `lint` script (ESLint not installed).
- [x] No error boundary, no 404 page (unknown routes redirect to `/`), no offline banner, no
      keyboard shortcuts, no multi-select or bulk actions, no undo.

## 10. App-shell findings from screenshots
- [x] Security nav item can show the browser focus outline instead of the active style.
- [x] No-plan state: full-width blue banner on every page plus three more "See plans" buttons.
- [x] Upload buttons remain enabled without a plan and silently navigate to billing.

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
- [x] Thumbnails and in-app preview — generated in the browser from the encrypted file (see design-system.md, "File viewer and thumbnails").
- [ ] Device location — only the IP address is stored.
- [ ] Payment status other than Paid (Failed / Refunded) — invoices are only created for paid orders.

## Verification (ui-revamp, final pass)
- `npm run build`, `vue-tsc --noEmit` and `eslint src` finish with zero errors; 22 unit tests pass
  (`errors.test.ts`, `useForm.test.ts`); backend `pytest` 62 passed with no backend changes.
- Greps over `src`: no `alert(`/`confirm(`/`prompt(` calls, no `<select`, no `console.` outside
  `lib/logger.ts`, no native `title=` tooltips, no rendered `err.message`, every `<form>` has
  `novalidate`. The production bundle contains no `console` calls.
- Fault injection (Puppeteer request interception) for sign-in, create folder, rename, upload,
  change password and purchase × 400 (field), 401, 403, 404, 409, 413, 429, 500 and offline:
  54/54 cases show designed copy, never raw server text, never a blank screen; 401 always ends on
  the sign-in page with "Your session expired".
- Every page at 375 / 768 / 1440 px in light and dark: no horizontal overflow or mobile zoom-out.
- Keyboard-only: sign in, skip link, `?` shortcuts dialog, ⌘K palette, N new folder, list
  navigation, Space select, F2 rename, Shift+F10 item menu, Delete, avatar menu and theme switch.
- Colour tokens: body and secondary text ≥ 4.5:1 and form-control borders ≥ 3:1 on every surface,
  in both themes.
