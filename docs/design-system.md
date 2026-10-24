# SmartSpace design system

How the frontend looks, behaves and talks. Read this before adding a screen. Every component
listed here is in `frontend/src/components/ui/`, and in development you can see them all at
**`/_design`**; that route doesn't exist in production builds.

## Rules that lint and review enforce

| Never | Use instead | Guard |
|---|---|---|
| `alert` / `confirm` / `prompt` | `confirmDialog()` (`lib/confirm.ts`), toasts (`lib/toast.ts`) | ESLint `no-alert` |
| Rendering `err.message` or any server text | `normalizeApiError(err).message` or `reportError(err)` | review + `isHumanText` filter |
| Native `<select>` | `UiSelect` | ESLint `vue/no-restricted-html-elements` |
| Native `title=` tooltips | `UiTooltip`, or `UiButton`'s `tooltip` / icon-only `ariaLabel` | review |
| Native checkbox / radio | `UiCheckbox`, `UiRadioGroup`, `UiSwitch`, `UiSegmented` | review |
| Browser validation bubbles | `<form novalidate>` + `useForm` | review |
| `console.*` | `logger` (`lib/logger.ts`, silent in production) | ESLint `no-console`; prod build strips `console` |
| A spinner in empty space | `UiSkeleton` shaped like the final layout | review |
| Hard-coded colours (`slate-500`, `#fff`) | semantic tokens below | review |
| `v-html` | text interpolation | ESLint `vue/no-v-html` |

## Tokens

Defined once in `src/design/tokens.css` as RGB triplets and exposed through Tailwind
(`tailwind.config.js`), so opacity works: `bg-primary/10`. Use the Tailwind names in markup.

### Colour

| Tailwind | Token | Use |
|---|---|---|
| `bg-canvas` / `bg-canvas-subtle` | `--bg`, `--bg-subtle` | Page background; hover rows, inputs on cards |
| `bg-surface` / `-raised` / `-sunken` | `--surface*` | Cards, menus and popovers, table headers |
| `border-line` / `border-line-strong` | `--border`, `--border-strong` | Dividers and cards / form-control borders (≥ 3:1) |
| `text-fg` / `-muted` / `-subtle` | `--text*` | Primary text / secondary / metadata and hints (all ≥ 4.5:1) |
| `primary`, `primary-hover`, `primary-fg`, `primary-soft`, `primary-soft-fg` | `--primary*` | One primary action per view, links, selection |
| `success` `warning` `danger` `info` + `-soft` | | Status text and tinted backgrounds; `danger-fg` on solid danger |
| `overlay` | `--overlay` | Modal backdrop |
| `brand-*` | static | Marketing illustrations only |

`--logo-accent` is only for the logo wordmark. The palette was checked against WCAG 2.2 AA in
both themes: text pairs ≥ 4.5:1, control boundaries ≥ 3:1. Re-check any new pair.

### Dark mode and theme

`stores/theme.ts` stores Light / Dark / System (`localStorage` key `sc_theme`) and sets
`data-theme` on `<html>`. With System, the `prefers-color-scheme` media query decides. Tailwind's
`dark:` variant follows the same rule, but you rarely need it: tokens already flip. The switcher
lives in the avatar menu.

### Type

Inter Variable is self-hosted (`@fontsource-variable/inter`) with `cv11` and `ss01` enabled. Use
`.tabular` for numbers that line up: sizes, prices, dates, counters.

| Class | Size / line | Use |
|---|---|---|
| `text-xs` | 12/16 | Badges, keyboard hints |
| `text-sm` | 13/18 | Metadata, hints, field errors, table headers |
| `text-base` | 14/20 | **Default UI text** |
| `text-md` | 16/24 | Card titles, prominent rows |
| `text-lg` | 20/28 | Section headings |
| `text-xl` | 24/32 | Page titles (`UiPageHeader`) |
| `text-2xl` | 30/36 | Big numbers (KPIs, storage) |
| `text-3xl`–`text-5xl` | 38–60 | Marketing pages only |

### Spacing, radius, elevation, motion

- Spacing is Tailwind's 4 px scale. In the app, pages use the full width beside the sidebar with
  16 / 24 px gutters (`px-4 sm:px-6`) and a 16–20 px top margin; forms and settings cap their own
  width (`max-w-4xl`, billing `max-w-6xl`). Marketing pages centre at `max-w-6xl`, sections
  `py-16 sm:py-20`.
- Motion: cards fade up on first paint (`animate-card-in`, staggered ≤ 300 ms), lift 2 px on hover,
  and marketing sections reveal on scroll (`v-reveal`). All motion is off under
  `prefers-reduced-motion`.
- Radius: `rounded-sm` 4 px, `rounded` 6 px (controls), `rounded-lg` 10 px (cards, menus),
  `rounded-xl` 14 px (modals, panels).
- Shadows: `shadow-xs` (cards, buttons), `shadow-sm`, `shadow-md` (menus, popovers), `shadow-xl`
  (modals, upload panel).
- Motion: `duration-fast` 120 ms (hover, press), `duration-base` 180 ms (menus, tabs),
  `duration-slow` 220 ms (drawers, modals), easing `ease-out`. Animations: `animate-fade-in`,
  `scale-in`, `pop-in`, `slide-up`, `slide-in-left/right`, `row-flash` (new or changed row),
  `shimmer` (skeletons). Everything respects `prefers-reduced-motion`.

## Layout

- **App shell** (`layouts/AppLayout.vue`):
  - The sidebar is 248 px at 1280 px and wider (collapsible) and a 64 px icon rail from 768 px.
  - Below 768 px it becomes a drawer.
  - The header is 56 px with search / ⌘K, upload status, help and the avatar menu.
  - The first Tab stop is "Skip to content".
- **Breakpoints:** 375 (phone), 768 (`md`, rail and tables), 1024 (`lg`), 1280 (`xl`, full sidebar).
  No page may scroll sideways at 375 px.
- Wide tables sit in `relative overflow-x-auto`. The `relative` is required: without it,
  `sr-only` labels escape the scroller and zoom the page out on phones.

## Components

| Component | Notes |
|---|---|
| `UiButton` | Variants: `primary` (one per view), `secondary` (default), `ghost`, `danger`, `danger-ghost`, `link`. Sizes `sm`, `md`, `lg`. `to` / `href` render a link. `loading` keeps the width. `iconOnly` requires `ariaLabel`, which is also the tooltip. A disabled button can still carry a `tooltip` saying why. |
| `UiSplitButton`, `UiDropdownMenu`, `UiContextMenu` | Take `MenuEntry[]` (`menuTypes.ts`): label, icon, shortcut, danger, separators, headings. |
| `UiFormField` | Label, hint, error, required / optional, counter. Children get `id`, `aria-describedby` and `aria-invalid` automatically. |
| `UiInput`, `UiPasswordInput`, `UiTextarea`, `UiSearchInput` | `UiPasswordInput` has show / hide and a Caps Lock warning. `UiSearchInput` shows the ⌘K hint. |
| `UiSelect` | A Reka Select, which turns into a searchable combobox above 8 options or with `searchable`. Use `block: false` in toolbars. |
| `UiCheckbox`, `UiRadioGroup`, `UiSwitch`, `UiSegmented` | `UiSegmented` is for 2–4 mutually exclusive views or periods and supports a badge (e.g. "Save 17%"). |
| `UiModal` | Focus trap, focuses the first field, bottom sheet on phones. Set `dismissible=false` while saving. |
| `UiDrawer` | Side panel, used for file details. |
| `UiTooltip` | 300 ms delay; supports a `shortcut`. |
| `UiTabs`, `UiBreadcrumbs`, `UiPagination`, `UiPageHeader`, `UiCard` | Layout building blocks. Breadcrumbs collapse into an overflow menu. |
| `UiAlert`, `UiBanner` | Alerts are inline, inside a form or card. Banners are full-width, slim and dismissible. |
| `UiBadge`, `UiAvatar`, `UiKbd` | `UiBadge` tones: `neutral`, `primary`, `success`, `warning`, `danger`, `info`; `dot` for status. |
| `UiProgress`, `UiProgressCircle`, `UiSkeleton`, `UiSpinner` | `UiSpinner` is only for inside buttons and small inline waits. |
| `UiEmptyState` | Icon, title, one sentence and at most one primary action. Tones `neutral`, `primary`, `danger` (load errors). |
| `UiConfirmHost` | Mounted once in `App.vue`. Open it through `confirmDialog()`. |

## Patterns

### Errors

- Every caught error goes through `normalizeApiError()` (`lib/errors.ts`). It returns
  `{kind, status, code, message, fieldErrors, retryable}`.
- Server text appears only when it reads like a sentence for people. Otherwise the fixed copy
  below is shown.
- 404, 409 and 413 use file wording only for file and upload requests (the API path is on
  `ApiError.path`).

| Case | Copy |
|---|---|
| Offline / network | We couldn't reach SmartSpace. Check your connection and try again. |
| 400 with field errors | Message under each field; banner: Please check the highlighted fields and try again. |
| Sign-in 400 / 401 | Email or password is incorrect. |
| 401 elsewhere | Your session expired. Please sign in again. (then the sign-in page) |
| 403 | You don't have access to this. |
| 404 | This item no longer exists. / This isn't available right now. Please try again later. |
| 409 | A file with this name already exists here. / This changed since you opened it. Refresh and try again. |
| 413 | This file is larger than your plan allows. (+ Upgrade) |
| 429 | Too many attempts. Try again in a minute. (or the server's lockout wording) |
| 5xx | Something went wrong on our side. Please try again. |
| No plan / grace / quota | Opens the plan picker with the reason |

- Use `reportError(err, {retry})` for actions that aren't forms. It opens the plan picker for plan
  and quota errors, does nothing for 401 (the API client already redirects), and shows a toast
  with Retry for everything else.
- `App.vue` is a global error boundary: a crashed screen or a page that fails to load shows a
  friendly page with Reload and Go to My files.

### Forms

- Use `useForm(initial, rules, {serverFieldMap})` with `<form novalidate>`.
- Errors appear on blur, then update live as the person types.
- Submitting focuses the first invalid field.
- Server field errors land under the matching field via `serverFieldMap`.
- Keep the submit button enabled, except where the requirement checklist is visible (passwords),
  and show `loading` while it runs.

### Confirmations, undo and toasts

- Prefer undo to confirm: `toast.undoable()` for trash, restore, move and rename.
- Confirm only what can't be undone: `confirmDialog({title, body, confirmLabel, danger, action})`.
  For bulk or account-wide destruction, add `typeToConfirm`.
- With `action`, the dialog keeps the button loading and shows the normalised error in place.
- Toasts appear bottom-right on desktop and top-centre on phones, above the upload panel. Use
  `toast.success` for short past-tense outcomes ("Folder created"), `toast.error(msg, {retry})`,
  and `toast.loading` for long work.

### Loading, empty and offline

- First load shows skeletons in the final layout; later refreshes keep content and dim it
  (`opacity-60`). Never let the layout jump.
- An empty state says what will appear and offers one action ("Upload files").
- A load error is a `danger` empty state with Try again.
- `OfflineBanner` sits above everything when the browser is offline. Uploads pause and resume
  automatically.

### File viewer and thumbnails

Files are end-to-end encrypted, so everything is decrypted in the browser.

- `lib/crypto/encryptedFile.ts` reads any byte range by fetching and decrypting only the 8–20 MB
  parts that cover it (HTTP Range on `/nodes/<id>/content`).
- `public/preview-sw.js` turns that into a normal streaming URL (`/__stream/<id>/<name>`) for
  `<video>` and `<audio>`, so playback starts at once and seeking fetches only what it needs. The
  worker holds no keys; it asks the page for bytes. Without a service worker, media up to 500 MB
  is decrypted into memory first.
- Thumbnails (`features/preview/thumbnails.ts`): images are scaled, videos give a frame at ~1 s,
  PDFs render page one. They load when a card scrolls into view, two at a time, and are cached in
  IndexedDB encrypted with a key derived from the vault key. Key requests for thumbnails use
  `?purpose=thumbnail` so they don't appear in account activity; opening the viewer logs
  "Opened a file".
- The viewer (`features/preview/FilePreview.vue`) is always dark (`data-theme="dark"` scope). It
  shows images (zoom, pan, pinch, swipe), video and audio, PDFs (pdf.js), Word `.docx`
  (docx-preview), spreadsheets and CSV (SheetJS) and text or code. Anything else, or a file the
  browser can't decode, gets a fallback with Download. Viewer libraries load only when needed.

### Keyboard

- Global: ⌘/Ctrl K command palette, `/` search, `N` new folder, `U` upload, `?` shortcuts.
- File list: arrows, Home / End, Space select, Shift + arrows to extend, ⌘/Ctrl A, Enter open,
  F2 rename, Shift+F10 item menu, Delete to trash, Esc clear.
- File viewer: ← / → previous and next file, + / − / 0 zoom images, Esc close.
- Every shortcut appears in the `?` dialog (`components/ShortcutsDialog.vue`). Add new ones there.

## Writing

- **Voice.** Sentence case everywhere. Plain words, second person. Name the thing, not the system:
  "Move to trash", not "Delete node".
- **Buttons.** Buttons are verbs that say what happens: "Create folder", "Pay ₹1,490",
  "Delete forever". Avoid "OK", "Submit" and "Yes".
- **Errors.** Errors say what happened and what to do next. Never blame the user, never show
  codes or stack traces.
- **Numbers and dates.** Numbers use `formatBytes` / `formatMoney` / `formatRelative`; exact
  timestamps go in a tooltip.
- **Truthfulness.** Copy must match behaviour. If the product can't do something (reset a vault
  password, carry over plan time), say so before the person commits. Open copy issues are in
  `docs/ui-audit.md` §11.

## Accessibility checklist (WCAG 2.2 AA)

- Every control has a visible label or an `aria-label`. Icon-only buttons need `ariaLabel`.
- Focus is always visible (`:focus-visible` ring) and never trapped, except inside modals.
  Modals return focus on close.
- Status changes are announced: field errors use `role="alert"`, counters and uploads use
  `aria-live="polite"`.
- Hit targets are at least 32 × 32 px (24 px minimum per 2.5.8); 44 px on touch layouts.
- Colour is never the only signal: statuses have text, and requirement lists have icons plus
  "(met)" / "(not met)" for screen readers.
- Respect `prefers-reduced-motion`. Don't rely on hover alone: hover actions on rows also live
  in the context menu and the bulk bar.
