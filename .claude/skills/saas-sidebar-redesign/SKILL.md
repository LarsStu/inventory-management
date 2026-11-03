---
name: saas-sidebar-redesign
description: Redesign a Vue 3 application's UI into a modern SaaS-style layout with a vertical left navigation sidebar (replacing a top nav bar), consistent spacing tokens, and a polished professional look. Use when asked to restyle the app shell, move navigation to a sidebar, modernize the UI, or make the layout look like a SaaS product. Applies to the inventory-management client in client/.
---

# SaaS Sidebar Redesign (Vue 3)

Turns the top-nav Vue 3 + Vite client into an app shell with a left sidebar, a sticky page header, a shared spacing scale, and a restrained visual system. Work in phases. Verify after each phase, not only at the end.

## Non-negotiable project rules

- **Delegate `.vue` work to `vue-expert`.** `CLAUDE.md` requires this for creating or significantly modifying any `.vue` file. Hand each phase below to that agent with the relevant file list and the design tokens from Phase 1. Review its output yourself afterwards.
- **No emojis in the UI.** Use inline SVG icons (stroke-based, `currentColor`, 20px, 1.75 stroke width).
- **Keep the existing palette family.** `CLAUDE.md` specifies slate/gray (`#0f172a`, `#64748b`, `#e2e8f0`) with green/blue/yellow/red for status. Accent may move to one primary color, but status colors stay.
- **Document non-obvious logic** with comments (e.g. why the sidebar state is persisted, why a z-index is what it is).
- **Both locales.** Any new UI string goes into `client/src/locales/en.js` and `client/src/locales/ja.js`. Japanese labels run longer; the sidebar must not truncate or wrap awkwardly.
- **Do not change behavior.** Filters, API calls (`client/src/api.js`), routing paths, and modal logic stay as they are. This is a presentation change.
- **Do not commit or stage.** The repo already has uncommitted changes (e.g. `client/src/App.vue`, `client/src/api.js`, `server/main.py`). Edit in place, never `git checkout`/`git stash` those files, and never revert changes you did not make.

## Phase 0: Survey (read before editing)

Read these and note what each one depends on:

1. `client/src/App.vue` — top nav markup, global styles (`<style>` is unscoped and holds the globals; `.nav-tabs`, `.logo`, `.main-content` etc. are defined here).
2. `client/src/main.js` — the route table. Current routes: `/`, `/inventory`, `/orders`, `/demand`, `/spending`, `/reports`, `/restocking`.
3. `client/src/components/FilterBar.vue`, `ProfileMenu.vue`, `LanguageSwitcher.vue` — these currently sit in the header/below it and must be relocated, not broken.
4. `client/src/locales/en.js` `nav` block — the existing nav labels to reuse.
5. Each `client/src/views/*.vue` root element and its class names. Before removing any global CSS from `App.vue`, grep for each selector you intend to remove (e.g. `grep -rn "nav-tabs" client/src`) to confirm nothing else depends on it.

Output of this phase: a short list of (a) global selectors that must survive, (b) components that move, (c) the nav items with their route and i18n key. Do not start editing until this list exists.

## Phase 1: Design tokens

Add CSS custom properties on `:root` in `App.vue`'s global style block, or in a new `client/src/styles/tokens.css` imported from `main.js` if the file is getting large. Use these as the starting values; adjust only with a reason:

```css
:root {
  /* Surfaces */
  --color-bg: #f8fafc;
  --color-surface: #ffffff;
  --color-surface-muted: #f1f5f9;
  --color-border: #e2e8f0;

  /* Text */
  --color-text: #0f172a;
  --color-text-secondary: #475569;
  --color-text-muted: #64748b;

  /* Accent (one primary) */
  --color-accent: #2563eb;
  --color-accent-soft: #eff6ff;
  --color-accent-hover: #1d4ed8;

  /* Sidebar */
  --sidebar-bg: #0f172a;
  --sidebar-text: #cbd5e1;
  --sidebar-text-active: #ffffff;
  --sidebar-hover-bg: #1e293b;
  --sidebar-active-bg: #1e3a8a;
  --sidebar-width: 248px;
  --sidebar-width-collapsed: 72px;

  /* Spacing scale (4px base) */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;

  /* Radius and elevation */
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --shadow-card: 0 1px 2px rgba(15, 23, 42, 0.04), 0 1px 3px rgba(15, 23, 42, 0.06);
  --shadow-overlay: 0 10px 25px rgba(15, 23, 42, 0.12);

  /* Type */
  --text-xs: 0.75rem;
  --text-sm: 0.875rem;
  --text-base: 0.9375rem;
  --text-lg: 1.125rem;
  --text-xl: 1.5rem;
}
```

Rules for the rest of the work:
- Replace hard-coded `px`/`rem` spacing in files you touch with the scale above. Do not rewrite every view's internals in one pass; convert incrementally, starting with the shell and the most-visited views (Dashboard, Inventory, Orders).
- Cards: `background: var(--color-surface)`, `border: 1px solid var(--color-border)`, `border-radius: var(--radius-lg)`, `box-shadow: var(--shadow-card)`. One card style, reused.
- Tables and KPI tiles should share header/row padding and font sizes; don't let each view pick its own.

## Phase 2: App shell with left sidebar

Target structure in `App.vue`:

```
.app (flex row, min-height 100vh)
├── AppSidebar.vue          (fixed/sticky, full height, left)
└── .app-body (flex column, flex: 1, min-width: 0)
    ├── .app-header         (sticky top, 64px, white, border-bottom)
    │   ├── page title area / menu toggle (mobile)
    │   └── right side: LanguageSwitcher, ProfileMenu
    ├── FilterBar           (below header, inside a padded strip)
    └── main.main-content   (max-width ~1600px, padding var(--space-6), margin auto)
        └── <router-view />
```

Requirements:
- **Create `client/src/components/AppSidebar.vue`.** Contents, top to bottom:
  - Logo block: company name (`nav.companyName`) with subtitle hidden when collapsed.
  - Grouped nav with small uppercase section labels, e.g. "Overview" (Dashboard), "Operations" (Inventory, Orders, Restocking, Demand), "Finance" (Spending), "Reports" (Reports). Group names are new strings: add to both locales.
  - Each item: inline SVG icon + label, `<router-link>`, `aria-current="page"` on the active link. Use `route.path` prefix matching, not exact equality, so nested routes stay highlighted.
  - Bottom: collapse toggle (desktop) and the `ProfileMenu` trigger, if it fits; otherwise keep ProfileMenu in the header.
- **Collapsible on desktop.** Width `--sidebar-width` ↔ `--sidebar-width-collapsed`. Persist the collapsed flag in `localStorage` under one key. Collapsed mode shows icons only with a `title` attribute (tooltip) and `aria-label` on each link.
- **Responsive below 1024px.** Sidebar becomes an off-canvas drawer opened by a menu button in the header. Show a backdrop overlay; close on backdrop click, on route change, and on `Escape`. Lock body scroll while open.
- **Z-index order:** sidebar and header below modals. Modals already exist (`TasksModal`, `ProfileDetailsModal`, detail modals); confirm they still overlay the sidebar and header after the change. Pick explicit values and comment them.
- **Remove** the old `.top-nav`, `.nav-container`, `.nav-tabs`, and `.logo` rules once nothing references them (verify with grep first).
- **Active-state styling:** left accent bar (3px) plus `--sidebar-active-bg`, not just a color change.

## Phase 3: Page header and content rhythm

- Add a small reusable `client/src/components/PageHeader.vue` (props: `title`, `description`; slot: `actions`). Views opt in incrementally; do not force every view in one step if it risks breaking its layout.
- Consistent vertical rhythm: `--space-6` between major sections, `--space-4` inside cards, `--space-3` between related controls.
- Headings: one page-level `h1` per view (`--text-xl`, weight 600, `--color-text`), section `h2` at `--text-lg`.
- Keep `FilterBar` visually attached to the content it filters: same left edge as `main` content, not full-bleed under the sidebar.

## Phase 4: Responsive and state checks

- Layout must hold at 1440px, 1024px, and 390px wide.
- Long tables scroll horizontally inside their card (`overflow-x: auto` on the wrapper), never push the page wider than the viewport.
- Japanese locale: switch with `LanguageSwitcher` and check the sidebar labels and the header do not overflow.
- Keep the existing loading/error states in every view; the redesign must not drop them.

## Verification (do all of these before reporting done)

1. `cd client && npm run build` — must succeed with no new warnings you introduced. Report any pre-existing warnings as pre-existing.
2. `cd client && npm run dev` (port 3000) with the API from `server/` running on port 8001.
3. Use the Playwright MCP tools (`mcp__playwright__*`, per `CLAUDE.md`) to load each route at 1440px and 390px and take screenshots. Check:
   - Sidebar highlights the correct item on every route.
   - No horizontal page scroll at 390px.
   - Drawer opens, closes on Escape and on overlay click.
   - Browser console has no new errors or Vue warnings.
   - Switch to Japanese and recheck the sidebar.
4. Grep for leftovers: `grep -rn "top-nav\|nav-tabs\|nav-container" client/src` should return nothing.
5. Grep for emoji in changed files (`grep -P "[\x{1F300}-\x{1FAFF}\x{2600}-\x{27BF}]"`) — should return nothing in UI templates.
6. Have `code-reviewer` review the diff of `App.vue`, `AppSidebar.vue`, and any locale changes.

## Report back

State: which files changed, which routes/views were checked and at what widths, build result, console-error result, and anything intentionally left for later (e.g. views not yet converted to tokens). Do not claim a view is "fully redesigned" if only the shell changed.
