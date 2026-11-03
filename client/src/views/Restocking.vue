<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrency as formatCurrencyUtil } from '../utils/currency'

const { t, currentCurrency } = useI18n()

const STEP = 1000

const forecasts = ref([])
const loading = ref(true)
const error = ref(null)
const budget = ref(0)
const excluded = ref(new Set())
const submitting = ref(false)
const submitError = ref(null)
const confirmation = ref(null)

const formatCurrency = (value) => formatCurrencyUtil(value, currentCurrency.value)

const getGap = (f) => Math.max((f.forecasted_demand || 0) - (f.current_demand || 0), 0)

const maxBudget = computed(() => {
  const total = forecasts.value.reduce((sum, f) => sum + f.unit_cost * getGap(f), 0)
  return Math.ceil(total / STEP) * STEP
})

const recommendations = computed(() => {
  let remaining = budget.value
  const result = []
  const candidates = forecasts.value
    .map(f => ({ f, gap: getGap(f) }))
    .filter(c => c.gap > 0 && c.f.unit_cost > 0)
    .sort((a, b) => b.gap - a.gap)
  for (const { f, gap } of candidates) {
    const qty = Math.min(gap, Math.floor(remaining / f.unit_cost))
    if (qty <= 0) continue
    remaining -= qty * f.unit_cost
    result.push({
      sku: f.item_sku,
      name: f.item_name,
      supplier: f.supplier,
      quantity: qty,
      unitCost: f.unit_cost,
      lineTotal: qty * f.unit_cost,
      leadTime: f.lead_time_days
    })
  }
  return result
})

const selected = computed(() => recommendations.value.filter(r => !excluded.value.has(r.sku)))
const selectedTotal = computed(() => selected.value.reduce((sum, r) => sum + r.lineTotal, 0))
const remainingBudget = computed(() => budget.value - selectedTotal.value)

const toggle = (sku, checked) => {
  const next = new Set(excluded.value)
  if (checked) next.delete(sku)
  else next.add(sku)
  excluded.value = next
}

const loadForecasts = async () => {
  try {
    loading.value = true
    error.value = null
    forecasts.value = await api.getDemandForecasts()
    budget.value = Math.round(maxBudget.value / 2 / STEP) * STEP
  } catch (err) {
    error.value = t('common.error') + ': ' + err.message
    console.error('Load error:', err)
  } finally {
    loading.value = false
  }
}

const placeOrder = async () => {
  if (selected.value.length === 0 || submitting.value) return
  submitting.value = true
  submitError.value = null
  confirmation.value = null
  try {
    const order = await api.createRestockingOrder({
      budget: budget.value,
      items: selected.value.map(i => ({ sku: i.sku, quantity: i.quantity }))
    })
    confirmation.value = order
  } catch (err) {
    submitError.value = err.response?.data?.detail || err.message
    console.error('Order submit error:', err)
  } finally {
    submitting.value = false
  }
}

onMounted(loadForecasts)
</script>

<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="card budget-card">
        <div class="budget-row">
          <label for="budget-slider" class="budget-label">{{ t('restocking.budget') }}</label>
          <span class="budget-value">{{ formatCurrency(budget) }}</span>
        </div>
        <input
          id="budget-slider"
          v-model.number="budget"
          type="range"
          class="budget-slider"
          min="0"
          :max="maxBudget"
          :step="STEP"
        />
      </div>

      <div class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.budget') }}</div>
          <div class="stat-value">{{ formatCurrency(budget) }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">{{ t('restocking.selectedTotal') }}</div>
          <div class="stat-value">{{ formatCurrency(selectedTotal) }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('restocking.remaining') }}</div>
          <div class="stat-value">{{ formatCurrency(remainingBudget) }}</div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommended') }} ({{ recommendations.length }})</h3>
          <button
            type="button"
            class="place-order-btn"
            :disabled="selected.length === 0 || submitting"
            @click="placeOrder"
          >
            {{ submitting ? t('restocking.submitting') : t('restocking.placeOrder') }}
          </button>
        </div>

        <div v-if="confirmation" class="confirmation" role="status">
          <span>{{ t('restocking.orderSubmitted', { orderNumber: confirmation.order_number, count: confirmation.lead_time_days }) }}</span>
          <router-link to="/orders">{{ t('restocking.viewOrders') }}</router-link>
        </div>
        <div v-if="submitError" class="submit-error" role="alert">
          {{ t('restocking.error') }}: {{ submitError }}
        </div>

        <div v-if="recommendations.length === 0" class="empty">{{ t('restocking.noRecommendations') }}</div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.include') }}</th>
                <th>{{ t('restocking.table.item') }}</th>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.supplier') }}</th>
                <th>{{ t('restocking.table.quantity') }}</th>
                <th>{{ t('restocking.table.unitCost') }}</th>
                <th>{{ t('restocking.table.lineTotal') }}</th>
                <th>{{ t('restocking.table.leadTime') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="rec in recommendations" :key="rec.sku">
                <td>
                  <input
                    type="checkbox"
                    :checked="!excluded.has(rec.sku)"
                    :aria-label="t('restocking.table.include')"
                    @change="toggle(rec.sku, $event.target.checked)"
                  />
                </td>
                <td><strong>{{ rec.name }}</strong></td>
                <td>{{ rec.sku }}</td>
                <td>{{ rec.supplier }}</td>
                <td>{{ rec.quantity }}</td>
                <td>{{ formatCurrency(rec.unitCost) }}</td>
                <td><strong>{{ formatCurrency(rec.lineTotal) }}</strong></td>
                <td>{{ t('restocking.leadTimeDays', { count: rec.leadTime }) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.budget-card {
  margin-bottom: 1.5rem;
  padding: 1.25rem 1.5rem;
}

.budget-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.75rem;
}

.budget-label {
  font-weight: 600;
  color: #0f172a;
}

.budget-value {
  font-weight: 600;
  font-size: 1.125rem;
  color: #0f172a;
}

.budget-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: #e2e8f0;
  outline: none;
  cursor: pointer;
}

.budget-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #0f172a;
  border: 2px solid white;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.4);
}

.budget-slider::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #0f172a;
  border: 2px solid white;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.4);
}

.budget-slider::-moz-range-track {
  height: 6px;
  border-radius: 3px;
  background: #e2e8f0;
}

.budget-slider:focus-visible {
  box-shadow: 0 0 0 3px #cbd5e1;
}

.place-order-btn {
  background: #0f172a;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 0.5rem 1rem;
  font-weight: 500;
  cursor: pointer;
}

.place-order-btn:hover:not(:disabled) {
  background: #1e293b;
}

.place-order-btn:disabled {
  background: #94a3b8;
  cursor: not-allowed;
}

.confirmation,
.submit-error {
  margin: 0 0 1rem;
  padding: 0.75rem 1rem;
  border-radius: 6px;
  display: flex;
  gap: 1rem;
  align-items: center;
  flex-wrap: wrap;
}

.confirmation {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #166534;
}

.confirmation a {
  color: #166534;
  font-weight: 600;
  text-decoration: underline;
}

.submit-error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
}

.empty {
  padding: 2rem;
  text-align: center;
  color: #64748b;
}
</style>
