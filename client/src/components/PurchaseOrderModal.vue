<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen && backlogItem" class="modal-overlay" @click="close">
        <div class="modal-container" role="dialog" aria-modal="true" @click.stop>
          <div class="modal-header">
            <h3 class="modal-title">{{ mode === 'view' ? 'Purchase Order' : 'Create Purchase Order' }}</h3>
            <button class="close-button" type="button" aria-label="Close" @click="close">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </button>
          </div>

          <!-- View mode -->
          <template v-if="mode === 'view'">
            <div class="modal-body">
              <div v-if="loading" class="state-message">Loading purchase order...</div>
              <div v-else-if="error" class="error-message">{{ error }}</div>
              <div v-else-if="purchaseOrder" class="info-grid">
                <div class="info-item">
                  <div class="info-label">PO ID</div>
                  <div class="info-value mono">{{ purchaseOrder.id }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">Status</div>
                  <div class="info-value">
                    <span class="badge" :class="statusClass">{{ purchaseOrder.status }}</span>
                  </div>
                </div>
                <div class="info-item">
                  <div class="info-label">Supplier</div>
                  <div class="info-value">{{ purchaseOrder.supplier_name }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">Quantity</div>
                  <div class="info-value">{{ purchaseOrder.quantity }} units</div>
                </div>
                <div class="info-item">
                  <div class="info-label">Unit Cost</div>
                  <div class="info-value">{{ formatCurrency(purchaseOrder.unit_cost) }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">Expected Delivery</div>
                  <div class="info-value">{{ formatDate(purchaseOrder.expected_delivery_date) }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">Created</div>
                  <div class="info-value">{{ formatDate(purchaseOrder.created_date) }}</div>
                </div>
                <div class="info-item full-width">
                  <div class="info-label">Notes</div>
                  <div class="info-value">{{ purchaseOrder.notes || 'None' }}</div>
                </div>
              </div>
            </div>
            <div class="modal-footer">
              <button class="btn-secondary" type="button" @click="close">Close</button>
            </div>
          </template>

          <!-- Create mode -->
          <form v-else novalidate @submit.prevent="submit" class="po-form">
            <div class="modal-body">
              <div class="item-summary">
                <div class="item-name">{{ backlogItem.item_name }}</div>
                <div class="item-meta">
                  SKU {{ backlogItem.item_sku }} &middot; Order {{ backlogItem.order_id }}
                </div>
              </div>

              <div v-if="error" class="error-message" role="alert">{{ error }}</div>

              <div class="form-grid">
                <div class="form-group full-width">
                  <label for="po-supplier">Supplier Name</label>
                  <input id="po-supplier" v-model="form.supplier_name" type="text" required />
                </div>
                <div class="form-group">
                  <label for="po-quantity">Quantity</label>
                  <input id="po-quantity" v-model.number="form.quantity" type="number" min="1" step="1" required />
                </div>
                <div class="form-group">
                  <label for="po-unit-cost">Unit Cost (USD)</label>
                  <input id="po-unit-cost" v-model.number="form.unit_cost" type="number" min="0.01" step="0.01" required />
                </div>
                <div class="form-group full-width">
                  <label for="po-date">Expected Delivery Date</label>
                  <input id="po-date" v-model="form.expected_delivery_date" type="date" required />
                </div>
                <div class="form-group full-width">
                  <label for="po-notes">Notes (optional)</label>
                  <textarea id="po-notes" v-model="form.notes" rows="3"></textarea>
                </div>
              </div>
            </div>
            <div class="modal-footer">
              <button class="btn-secondary" type="button" @click="close">Cancel</button>
              <button class="btn-primary" type="submit" :disabled="submitting">
                {{ submitting ? 'Creating...' : 'Create PO' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script>
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import { api } from '../api'

export default {
  name: 'PurchaseOrderModal',
  props: {
    isOpen: { type: Boolean, default: false },
    backlogItem: { type: Object, default: null },
    mode: { type: String, default: 'create' }
  },
  emits: ['close', 'po-created'],
  setup(props, { emit }) {
    const form = reactive({
      supplier_name: '',
      quantity: 1,
      unit_cost: null,
      expected_delivery_date: '',
      notes: ''
    })
    const purchaseOrder = ref(null)
    const loading = ref(false)
    const submitting = ref(false)
    const error = ref(null)

    // Default quantity is the shortage (needed minus available), never below 1
    const defaultQuantity = computed(() => {
      if (!props.backlogItem) return 1
      const shortage = props.backlogItem.quantity_needed - props.backlogItem.quantity_available
      return Number.isFinite(shortage) && shortage > 0 ? Math.ceil(shortage) : 1
    })

    const statusClass = computed(() => {
      const status = (purchaseOrder.value?.status || '').toLowerCase()
      if (['delivered', 'received', 'completed'].includes(status)) return 'success'
      if (['cancelled', 'canceled'].includes(status)) return 'danger'
      if (['pending', 'ordered', 'in_transit', 'shipped'].includes(status)) return 'info'
      return 'neutral'
    })

    const resetState = () => {
      form.supplier_name = ''
      form.quantity = defaultQuantity.value
      form.unit_cost = null
      form.expected_delivery_date = ''
      form.notes = ''
      purchaseOrder.value = null
      error.value = null
      loading.value = false
      submitting.value = false
    }

    const errorMessage = (err, fallback) => {
      const detail = err?.response?.data?.detail
      // FastAPI validation errors return detail as an array of {msg} objects
      if (Array.isArray(detail)) return detail.map(d => d.msg).filter(Boolean).join('; ') || fallback
      return typeof detail === 'string' && detail ? detail : fallback
    }

    const loadPurchaseOrder = async () => {
      loading.value = true
      error.value = null
      try {
        // Backlog item ids are stringified because the API path/body expects string ids
        // while the dashboard data may provide them as numbers.
        purchaseOrder.value = await api.getPurchaseOrderByBacklogItem(String(props.backlogItem.id))
      } catch (err) {
        error.value = errorMessage(err, 'Failed to load purchase order')
        console.error('Purchase order load error:', err)
      } finally {
        loading.value = false
      }
    }

    const submit = async () => {
      if (submitting.value) return
      error.value = null

      const supplier = form.supplier_name.trim()
      if (!supplier) { error.value = 'Supplier name is required'; return }
      if (!Number.isInteger(form.quantity) || form.quantity < 1) {
        error.value = 'Quantity must be a positive whole number'; return
      }
      if (typeof form.unit_cost !== 'number' || !(form.unit_cost > 0)) {
        error.value = 'Unit cost must be greater than 0'; return
      }
      if (!form.expected_delivery_date) { error.value = 'Expected delivery date is required'; return }

      submitting.value = true
      try {
        const po = await api.createPurchaseOrder({
          backlog_item_id: String(props.backlogItem.id), // see note in loadPurchaseOrder
          supplier_name: supplier,
          quantity: form.quantity,
          unit_cost: form.unit_cost,
          expected_delivery_date: form.expected_delivery_date,
          notes: form.notes
        })
        emit('po-created', po)
        emit('close')
      } catch (err) {
        error.value = errorMessage(err, 'Failed to create purchase order')
        console.error('Purchase order create error:', err)
      } finally {
        submitting.value = false
      }
    }

    const close = () => emit('close')

    const onKeydown = (e) => {
      if (e.key === 'Escape' && props.isOpen) close()
    }

    // Reset (and fetch in view mode) every time the modal opens or a different item is shown
    watch(
      () => [props.isOpen, props.backlogItem?.id, props.mode],
      () => {
        if (!props.isOpen || !props.backlogItem) return
        resetState()
        if (props.mode === 'view') loadPurchaseOrder()
      },
      { immediate: true }
    )

    onMounted(() => document.addEventListener('keydown', onKeydown))
    onUnmounted(() => document.removeEventListener('keydown', onKeydown))

    const formatDate = (value) => {
      if (!value) return 'N/A'
      const date = new Date(value)
      if (isNaN(date.getTime())) return value
      return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
    }

    const formatCurrency = (value) => {
      const n = Number(value)
      if (!Number.isFinite(n)) return 'N/A'
      return n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
    }

    return {
      form,
      purchaseOrder,
      loading,
      submitting,
      error,
      statusClass,
      submit,
      close,
      formatDate,
      formatCurrency
    }
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 1rem;
}

.modal-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.15);
  max-width: 600px;
  width: 100%;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.po-form {
  display: flex;
  flex-direction: column;
  min-height: 0;
  flex: 1;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem;
  border-bottom: 1px solid #e2e8f0;
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.close-button {
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
  padding: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.15s ease;
}

.close-button:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
}

.item-summary {
  padding-bottom: 1rem;
  margin-bottom: 1.25rem;
  border-bottom: 1px solid #e2e8f0;
}

.item-name {
  font-size: 1.125rem;
  font-weight: 700;
  color: #0f172a;
}

.item-meta {
  margin-top: 0.25rem;
  font-size: 0.875rem;
  color: #64748b;
  font-family: 'Monaco', 'Courier New', monospace;
}

.form-grid,
.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.25rem;
}

.full-width {
  grid-column: 1 / -1;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label,
.info-label {
  font-size: 0.813rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
}

.form-group input,
.form-group textarea {
  padding: 0.625rem 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.938rem;
  font-family: inherit;
  color: #0f172a;
  background: white;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.form-group textarea {
  resize: vertical;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #64748b;
  box-shadow: 0 0 0 3px rgba(100, 116, 139, 0.15);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.info-value {
  font-size: 0.938rem;
  color: #0f172a;
  font-weight: 500;
  word-break: break-word;
}

.info-value.mono {
  font-family: 'Monaco', 'Courier New', monospace;
  color: #2563eb;
}

.badge {
  display: inline-block;
  padding: 0.25rem 0.625rem;
  border-radius: 6px;
  font-size: 0.813rem;
  font-weight: 600;
  text-transform: capitalize;
}

.badge.success { background: #dcfce7; color: #166534; }
.badge.info { background: #dbeafe; color: #1e40af; }
.badge.danger { background: #fecaca; color: #991b1b; }
.badge.neutral { background: #f1f5f9; color: #334155; }

.state-message {
  text-align: center;
  color: #64748b;
  padding: 2rem 0;
}

.error-message {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  font-size: 0.875rem;
  margin-bottom: 1.25rem;
}

.modal-footer {
  padding: 1.5rem;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.btn-secondary,
.btn-primary {
  padding: 0.625rem 1.25rem;
  border-radius: 8px;
  font-weight: 500;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.btn-secondary {
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  color: #334155;
}

.btn-secondary:hover {
  background: #e2e8f0;
  border-color: #cbd5e1;
}

.btn-primary {
  background: #0f172a;
  border: 1px solid #0f172a;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #1e293b;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Modal transition animations */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .modal-container,
.modal-leave-active .modal-container {
  transition: transform 0.2s ease;
}

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  transform: scale(0.95);
}
</style>
