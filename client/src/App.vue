<template>
  <div class="app" :class="{ 'sidebar-rail': !isMobile && sidebarCollapsed }">
    <AppSidebar
      :collapsed="sidebarIconOnly"
      @toggle-collapse="toggleSidebar"
    />

    <!-- Mobile overlay backdrop: only exists while the rail is expanded below 1024px. -->
    <div
      v-if="isMobile && overlayOpen"
      class="sidebar-backdrop"
      @click="closeOverlay"
    />

    <div class="app-body">
      <header class="app-header">
        <div class="header-actions">
          <LanguageSwitcher />
          <ProfileMenu
            @show-profile-details="showProfileDetails = true"
            @show-tasks="showTasks = true"
          />
        </div>
      </header>
      <FilterBar />
      <main class="main-content">
        <router-view />
      </main>
    </div>

    <ProfileDetailsModal
      :is-open="showProfileDetails"
      @close="showProfileDetails = false"
    />

    <TasksModal
      :is-open="showTasks"
      :tasks="tasks"
      @close="showTasks = false"
      @add-task="addTask"
      @delete-task="deleteTask"
      @toggle-task="toggleTask"
    />
  </div>
</template>

<script>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from './api'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import AppSidebar from './components/AppSidebar.vue'
import FilterBar from './components/FilterBar.vue'
import ProfileMenu from './components/ProfileMenu.vue'
import ProfileDetailsModal from './components/ProfileDetailsModal.vue'
import TasksModal from './components/TasksModal.vue'
import LanguageSwitcher from './components/LanguageSwitcher.vue'

// Desktop collapse preference. One key, value '1' = collapsed, '0' = expanded.
// Only used at >=1024px; below that the sidebar state is session-only.
const SIDEBAR_COLLAPSED_KEY = 'app-sidebar-collapsed'
// Must match the breakpoint in AppSidebar/App styles (1024px).
const MOBILE_QUERY = '(max-width: 1023px)'

const readStoredCollapsed = () => {
  try {
    return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === '1'
  } catch (err) {
    // Storage can be blocked (privacy mode); fall back to expanded.
    return false
  }
}

export default {
  name: 'App',
  components: {
    AppSidebar,
    FilterBar,
    ProfileMenu,
    ProfileDetailsModal,
    TasksModal,
    LanguageSwitcher
  },
  setup() {
    const { currentUser } = useAuth()
    const { t } = useI18n()
    const route = useRoute()
    const showProfileDetails = ref(false)
    const showTasks = ref(false)
    const apiTasks = ref([])

    // --- Sidebar layout state ---
    // Two independent modes share one sidebar component:
    //  - >=1024px: sidebarCollapsed (persisted) toggles between full and icon-only.
    //  - <1024px: the sidebar is always an icon-only rail by default; overlayOpen
    //    expands it as a fixed overlay on top of the content (content never shifts).
    const mediaQuery = window.matchMedia(MOBILE_QUERY)
    const isMobile = ref(mediaQuery.matches)
    const sidebarCollapsed = ref(readStoredCollapsed())
    const overlayOpen = ref(false)

    // Icon-only state actually passed to the sidebar.
    const sidebarIconOnly = computed(() => {
      return isMobile.value ? !overlayOpen.value : sidebarCollapsed.value
    })

    const toggleSidebar = () => {
      if (isMobile.value) {
        overlayOpen.value = !overlayOpen.value
        return
      }
      sidebarCollapsed.value = !sidebarCollapsed.value
      try {
        localStorage.setItem(SIDEBAR_COLLAPSED_KEY, sidebarCollapsed.value ? '1' : '0')
      } catch (err) {
        // Ignore: the toggle still works for this session.
      }
    }

    const closeOverlay = () => {
      overlayOpen.value = false
    }

    // Close the overlay after navigating so the user lands on the new page.
    watch(() => route.path, closeOverlay)

    // Lock page scroll while the overlay is open so the backdrop does not scroll the page behind it.
    watch(overlayOpen, (open) => {
      document.body.style.overflow = open ? 'hidden' : ''
    })

    const onMediaChange = (event) => {
      isMobile.value = event.matches
      // Leaving mobile width should never leave a stale overlay or scroll lock behind.
      if (!event.matches) closeOverlay()
    }

    const onKeydown = (event) => {
      if (event.key === 'Escape' && overlayOpen.value) closeOverlay()
    }

    onMounted(() => {
      mediaQuery.addEventListener('change', onMediaChange)
      window.addEventListener('keydown', onKeydown)
    })

    onUnmounted(() => {
      mediaQuery.removeEventListener('change', onMediaChange)
      window.removeEventListener('keydown', onKeydown)
      document.body.style.overflow = ''
    })

    // Merge mock tasks from currentUser with API tasks
    const tasks = computed(() => {
      return [...currentUser.value.tasks, ...apiTasks.value]
    })

    const loadTasks = async () => {
      try {
        apiTasks.value = await api.getTasks()
      } catch (err) {
        console.error('Failed to load tasks:', err)
      }
    }

    const addTask = async (taskData) => {
      try {
        const newTask = await api.createTask(taskData)
        // Add new task to the beginning of the array
        apiTasks.value.unshift(newTask)
      } catch (err) {
        console.error('Failed to add task:', err)
      }
    }

    const deleteTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const isMockTask = currentUser.value.tasks.some(t => t.id === taskId)

        if (isMockTask) {
          // Remove from mock tasks
          const index = currentUser.value.tasks.findIndex(t => t.id === taskId)
          if (index !== -1) {
            currentUser.value.tasks.splice(index, 1)
          }
        } else {
          // Remove from API tasks
          await api.deleteTask(taskId)
          apiTasks.value = apiTasks.value.filter(t => t.id !== taskId)
        }
      } catch (err) {
        console.error('Failed to delete task:', err)
      }
    }

    const toggleTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const mockTask = currentUser.value.tasks.find(t => t.id === taskId)

        if (mockTask) {
          // Toggle mock task status
          mockTask.status = mockTask.status === 'pending' ? 'completed' : 'pending'
        } else {
          // Toggle API task
          const updatedTask = await api.toggleTask(taskId)
          const index = apiTasks.value.findIndex(t => t.id === taskId)
          if (index !== -1) {
            apiTasks.value[index] = updatedTask
          }
        }
      } catch (err) {
        console.error('Failed to toggle task:', err)
      }
    }

    onMounted(loadTasks)

    return {
      t,
      isMobile,
      sidebarCollapsed,
      sidebarIconOnly,
      overlayOpen,
      toggleSidebar,
      closeOverlay,
      showProfileDetails,
      showTasks,
      tasks,
      addTask,
      deleteTask,
      toggleTask
    }
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  background: var(--color-bg);
  color: #1e293b;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/*
 * App shell. The sidebar is position: fixed (see AppSidebar.vue); .app-body reserves
 * its width with margin-left so the content never sits underneath it.
 */
.app {
  min-height: 100vh;
}

/* Below 1024px the sidebar is always an icon rail (overlay expansion does not push content). */
.app-body {
  min-width: 0;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  margin-left: var(--sidebar-width-collapsed);
  transition: margin-left 0.2s ease;
}

@media (min-width: 1024px) {
  .app-body {
    margin-left: var(--sidebar-width);
  }

  /* Desktop collapse preference: the rail width is used when the user collapses. */
  .app.sidebar-rail .app-body {
    margin-left: var(--sidebar-width-collapsed);
  }
}

/*
 * Scrim behind the expanded mobile sidebar. Sits above page content and the sticky
 * header (z 100) and filter bar (z 90), below the sidebar (z 200) and modals (1000+).
 */
.sidebar-backdrop {
  position: fixed;
  inset: 0;
  z-index: var(--z-backdrop);
  background: rgba(15, 23, 42, 0.45);
}

.app-header {
  position: sticky;
  top: 0;
  z-index: var(--z-header);
  height: var(--header-height);
  display: flex;
  align-items: center;
  padding: 0 var(--space-6);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.header-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

@media (max-width: 640px) {
  .app-header {
    padding: 0 var(--space-4);
  }
}

.main-content {
  flex: 1;
  min-width: 0;
  max-width: 1600px;
  width: 100%;
  margin: 0 auto;
  padding: var(--space-6);
}

/* Narrow screens: tighter gutters so tables and cards get more of the 390px width. */
@media (max-width: 640px) {
  .main-content {
    padding: var(--space-4);
  }
}

.page-header {
  margin-bottom: 1.5rem;
}

.page-header h2 {
  font-size: 1.875rem;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 0.375rem;
  letter-spacing: -0.025em;
}

.page-header p {
  color: #64748b;
  font-size: 0.938rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.25rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  background: var(--color-surface);
  padding: var(--space-5);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-card);
  transition: all 0.2s ease;
}

.stat-card:hover {
  border-color: #cbd5e1;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.stat-label {
  color: #64748b;
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.625rem;
}

.stat-value {
  font-size: 2.25rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.stat-card.warning .stat-value {
  color: #ea580c;
}

.stat-card.success .stat-value {
  color: #059669;
}

.stat-card.danger .stat-value {
  color: #dc2626;
}

.stat-card.info .stat-value {
  color: #2563eb;
}

/* Single card style shared by all views (see tokens.css). */
.card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-card);
  margin-bottom: var(--space-6);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.card-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.table-container {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
  border-bottom: 1px solid #e2e8f0;
}

th {
  text-align: left;
  padding: 0.5rem 0.75rem;
  font-weight: 600;
  color: #475569;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

td {
  padding: 0.5rem 0.75rem;
  border-top: 1px solid #f1f5f9;
  color: #334155;
  font-size: 0.875rem;
}

tbody tr {
  transition: background-color 0.15s ease;
}

tbody tr:hover {
  background: #f8fafc;
}

.badge {
  display: inline-block;
  padding: 0.313rem 0.75rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.badge.success {
  background: #d1fae5;
  color: #065f46;
}

.badge.warning {
  background: #fed7aa;
  color: #92400e;
}

.badge.danger {
  background: #fecaca;
  color: #991b1b;
}

.badge.info {
  background: #dbeafe;
  color: #1e40af;
}

.badge.increasing {
  background: #d1fae5;
  color: #065f46;
}

.badge.decreasing {
  background: #fecaca;
  color: #991b1b;
}

.badge.stable {
  background: #e0e7ff;
  color: #3730a3;
}

.badge.high {
  background: #fecaca;
  color: #991b1b;
}

.badge.medium {
  background: #fed7aa;
  color: #92400e;
}

.badge.low {
  background: #dbeafe;
  color: #1e40af;
}

.loading {
  text-align: center;
  padding: 3rem;
  color: #64748b;
  font-size: 0.938rem;
}

.error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
  padding: 1rem;
  border-radius: 8px;
  margin: 1rem 0;
  font-size: 0.938rem;
}
</style>
