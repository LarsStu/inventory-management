<template>
  <aside
    class="app-sidebar"
    :class="{ 'is-collapsed': collapsed }"
    :aria-label="t('nav.mainMenu')"
  >
    <div class="sidebar-brand">
      <div class="brand-mark" aria-hidden="true">
        <svg class="nav-icon" viewBox="0 0 24 24">
          <path :d="icons.brand" />
        </svg>
      </div>
      <div class="brand-text">
        <div class="brand-name">{{ t('nav.companyName') }}</div>
        <div class="brand-subtitle">{{ t('nav.subtitle') }}</div>
      </div>
    </div>

    <nav class="sidebar-nav">
      <div v-for="group in navGroups" :key="group.id" class="nav-group">
        <div class="nav-group-label">{{ t(group.labelKey) }}</div>
        <ul class="nav-list">
          <li v-for="item in group.items" :key="item.to">
            <router-link
              :to="item.to"
              class="nav-link"
              :class="{ active: isActive(item.to) }"
              :aria-current="isActive(item.to) ? 'page' : undefined"
              :aria-label="t(item.labelKey)"
              :title="collapsed ? t(item.labelKey) : undefined"
            >
              <svg class="nav-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path :d="icons[item.icon]" />
              </svg>
              <span class="nav-label">{{ t(item.labelKey) }}</span>
            </router-link>
          </li>
        </ul>
      </div>
    </nav>

    <div class="sidebar-footer">
      <button
        type="button"
        class="collapse-toggle"
        :aria-label="collapsed ? t('nav.expandSidebar') : t('nav.collapseSidebar')"
        :title="collapsed ? t('nav.expandSidebar') : t('nav.collapseSidebar')"
        @click="$emit('toggle-collapse')"
      >
        <svg class="nav-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
          <path :d="icons.collapse" />
        </svg>
        <span class="nav-label">{{ t('nav.collapseSidebar') }}</span>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { useI18n } from '../composables/useI18n'

// `collapsed` means icon-only rail. App.vue decides whether that comes from the
// desktop persisted preference (>=1024px) or the mobile rail/overlay state (<1024px).
defineProps({
  collapsed: {
    type: Boolean,
    default: false
  }
})

defineEmits(['toggle-collapse'])

const { t } = useI18n()
const route = useRoute()

// SVG path data (24x24 outline icons, stroke-based, rendered with currentColor).
// Each icon is one `d` string so the template does not need a v-for over path parts.
const icons = {
  brand: 'M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z',
  dashboard: 'M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z',
  inventory: 'M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4',
  orders: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2M9 12h6M9 16h6',
  restocking: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15',
  demand: 'M3 17l6-6 4 4 8-8M14 7h7v7',
  finance: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  reports: 'M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
  // Double chevron pointing left; rotated 180deg via CSS when collapsed.
  collapse: 'M11 19l-7-7 7-7m8 14l-7-7 7-7'
}

// Grouped navigation. Route paths are the same as main.js; only grouping is new.
const navGroups = [
  {
    id: 'overview',
    labelKey: 'nav.groups.overview',
    items: [
      { to: '/', labelKey: 'nav.overview', icon: 'dashboard' }
    ]
  },
  {
    id: 'operations',
    labelKey: 'nav.groups.operations',
    items: [
      { to: '/inventory', labelKey: 'nav.inventory', icon: 'inventory' },
      { to: '/orders', labelKey: 'nav.orders', icon: 'orders' },
      { to: '/restocking', labelKey: 'nav.restocking', icon: 'restocking' },
      { to: '/demand', labelKey: 'nav.demandForecast', icon: 'demand' }
    ]
  },
  {
    id: 'finance',
    labelKey: 'nav.groups.finance',
    items: [
      { to: '/spending', labelKey: 'nav.finance', icon: 'finance' }
    ]
  },
  {
    id: 'reports',
    labelKey: 'nav.groups.reports',
    items: [
      { to: '/reports', labelKey: 'nav.reports', icon: 'reports' }
    ]
  }
]

// Prefix match so nested routes (e.g. /orders/123) keep their parent highlighted.
// '/' is the exception: it would otherwise match every route.
const isActive = (to) => {
  const path = route.path
  if (to === '/') return path === '/'
  return path === to || path.startsWith(to + '/')
}
</script>

<style scoped>
.app-sidebar {
  position: fixed;
  top: 0;
  bottom: 0;
  left: 0;
  /* Above the app header (z 100) and the mobile backdrop (z 190); below modals (z 1000+). */
  z-index: var(--z-sidebar);
  width: var(--sidebar-width);
  display: flex;
  flex-direction: column;
  background: var(--sidebar-bg);
  color: var(--sidebar-text);
  /* Width transition is shared by desktop collapse and the mobile rail/overlay toggle. */
  transition: width 0.2s ease;
}

.app-sidebar.is-collapsed {
  width: var(--sidebar-width-collapsed);
}

.sidebar-brand {
  flex-shrink: 0;
  height: var(--header-height);
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 0 var(--space-4);
  border-bottom: 1px solid var(--sidebar-divider);
}

.brand-mark {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  background: var(--sidebar-accent);
  color: #ffffff;
}

.brand-text {
  min-width: 0;
}

.brand-name {
  font-size: var(--text-sm);
  font-weight: 600;
  color: #ffffff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.brand-subtitle {
  font-size: var(--text-xs);
  color: var(--sidebar-text-muted);
  white-space: nowrap;
}

.sidebar-nav {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: var(--space-4) var(--space-3);
}

.nav-group + .nav-group {
  margin-top: var(--space-5);
}

.nav-group-label {
  padding: 0 var(--space-3) var(--space-2);
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--sidebar-text-muted);
  white-space: nowrap;
}

.nav-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.nav-link,
.collapse-toggle {
  position: relative;
  height: 40px;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 0 var(--space-3);
  border: 0;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--sidebar-text);
  font: inherit;
  font-size: var(--text-sm);
  font-weight: 500;
  text-decoration: none;
  white-space: nowrap;
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.nav-link:hover,
.collapse-toggle:hover {
  background: var(--sidebar-hover-bg);
  color: var(--sidebar-text-active);
}

.nav-link.active {
  background: var(--sidebar-active-bg);
  color: var(--sidebar-text-active);
}

/*
 * Active accent bar. It sits on the sidebar's left edge (the -12px offsets the
 * nav padding) so it stays visible in icon-only mode too.
 */
.nav-link.active::before {
  content: '';
  position: absolute;
  left: -12px;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--sidebar-accent);
}

.nav-link:focus-visible,
.collapse-toggle:focus-visible {
  outline: 2px solid var(--sidebar-accent);
  outline-offset: -2px;
}

.nav-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.75;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.sidebar-footer {
  flex-shrink: 0;
  padding: var(--space-3);
  border-top: 1px solid var(--sidebar-divider);
}

.collapse-toggle {
  width: 100%;
}

.collapse-toggle .nav-icon {
  transition: transform 0.2s ease;
}

/*
 * Icon-only mode. Labels are display:none rather than hidden with width or opacity,
 * so the remaining icons do not reflow; icons are centred in the rail so they keep
 * a fixed position while the sidebar width animates.
 */
.is-collapsed .brand-text,
.is-collapsed .nav-group-label,
.is-collapsed .nav-label {
  display: none;
}

.is-collapsed .sidebar-brand {
  justify-content: center;
  padding: 0;
}

.is-collapsed .nav-link,
.is-collapsed .collapse-toggle {
  justify-content: center;
  padding: 0;
}

.is-collapsed .nav-group + .nav-group {
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--sidebar-divider);
}

.is-collapsed .collapse-toggle .nav-icon {
  transform: rotate(180deg);
}
</style>
