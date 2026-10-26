<template>
  <div class="modal-panel max-w-3xl mx-auto" :class="{ 'h-full': !isModal }">
    
    <!-- Loading State -->
    <div v-if="loading" class="p-16 flex flex-col justify-center items-center gap-3">
      <span class="material-symbols-outlined animate-spin text-4xl text-accent dark:text-accent-light">progress_activity</span>
      <p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">Loading salary component details...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="!component" class="p-16 flex flex-col justify-center items-center gap-3">
      <span class="material-symbols-outlined text-4xl text-[#656A72] dark:text-white/60">error</span>
      <p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">Could not load salary component details.</p>
    </div>

    <!-- Content -->
    <template v-else>
      
      <!-- Top Status & Action Banner -->
      <header class="modal-header">
        <div class="flex items-center gap-3 min-w-0">
          <div class="w-12 h-12 rounded-[12px] flex items-center justify-center shrink-0" :class="getTypeBadgeBg(component.type)">
            <span class="material-symbols-outlined text-2xl" :class="getTypeTextColor(component.type)">
              {{ component.type === 'Deduction' ? 'remove_circle_outline' : 'payments' }}
            </span>
          </div>
          <div>
            <div class="flex items-center gap-2 mb-1">
              <p class="status-label">Salary component</p>
              <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold tag-neutral font-mono">
                {{ component.salary_component_abbr || component.name }}
              </span>
            </div>
            <h3 class="modal-title truncate">{{ component.salary_component || component.name }}</h3>
          </div>
        </div>

        <div class="flex items-center gap-3 relative self-end sm:self-center">
          <!-- Type Badge -->
          <span class="premium-tag" :class="getTypeBadgeClasses(component.type)">
            {{ component.type }}
          </span>

          <!-- Disabled / Active Status -->
          <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold" :class="component.disabled ? 'tag-amber' : 'bg-accent/[0.10] border-accent/30 text-accent dark:bg-accent/20 dark:border-accent/30 dark:text-accent-light'">
            {{ component.disabled ? 'Disabled' : 'Active' }}
          </span>

          <!-- Action Dropdown Button -->
          <RowActions v-if="canEdit || canDelete" :actions="[
          		{ label: 'Edit', icon: 'edit', show: !!(canEdit), onClick: () => { handleEdit() } },
          		{ divider: true },
          		{ label: 'Delete', icon: 'delete', danger: true, show: !!(canDelete), onClick: () => { handleDelete() } },
          	]" />

          <!-- Close Button -->
          <button 
            @click="$emit('close')"
            class="btn-icon-ghost shrink-0"
            title="Close"
           aria-label="Close"><span class="material-symbols-outlined !text-[18px]">close</span></button>
          
          <!-- Dropdown Menu -->
        </div>
      </header>

      <div class="flex-1 overflow-y-auto px-6 py-5">
      <!-- General Info Grid -->
      <div class="modal-section grid grid-cols-1 md:grid-cols-3 gap-6">
        <div>
          <p class="status-label">Component name</p>
          <p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ component.salary_component || component.name }}</p>
        </div>

        <div>
          <p class="status-label">Abbreviation</p>
          <p class="field-static !w-auto inline-block font-mono">
            {{ component.salary_component_abbr || '-' }}
          </p>
        </div>

        <div>
          <p class="status-label">Component type</p>
          <p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ component.type }}</p>
        </div>

        <div class="col-span-1 md:col-span-3">
          <p class="status-label">Description</p>
          <p class="inset-panel">
            {{ component.description || 'No description provided.' }}
          </p>
        </div>
      </div>

      <!-- Options Enabled Section -->
      <div class="modal-section flex flex-col gap-4">
        <div class="flex items-center justify-between">
          <div>
            <h4 class="status-label flex items-center gap-2">
              <span class="material-symbols-outlined text-accent dark:text-accent-light text-base">tune</span>
              Options Enabled
            </h4>
            <p class="text-xs text-[#5C6169] dark:text-white/65 mt-0.5">Configuration behavior and tax rules for this component.</p>
          </div>
          <span class="premium-tag tag-accent">
            {{ enabledOptionsCount }} active
          </span>
        </div>

        <!-- Options Grid -->
        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
          <div 
            v-for="opt in configuredOptionsList" 
            :key="opt.key" 
            class="p-3.5 rounded-[12px] border transition-all flex items-start gap-3"
            :class="opt.enabled ? 'bg-accent/[0.10] dark:bg-accent/20 border-accent/30 dark:border-accent/30' : 'bg-white dark:bg-surface-1/30 border-black/[0.07] dark:border-white/10 opacity-60'"
          >
            <div 
              class="w-6 h-6 rounded-full flex items-center justify-center shrink-0 mt-0.5"
              :class="opt.enabled ? 'bg-accent text-white' : 'bg-black/[0.08] dark:bg-white/[0.08] text-[#656A72] dark:text-white/55'"
            >
              <span class="material-symbols-outlined !text-[16px]">
                {{ opt.enabled ? 'check' : 'close' }}
              </span>
            </div>
            <div>
              <p class="text-[13px] font-medium" :class="opt.enabled ? 'text-[#17181B] dark:text-white' : 'text-[#5C6169] dark:text-white/65'">
                {{ opt.label }}
              </p>
              <p class="text-xs mt-0.5" :class="opt.enabled ? 'text-[#5C6169] dark:text-white/85' : 'text-[#656A72] dark:text-white/55'">
                {{ opt.description }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- Calculation & Formula Section -->
      <div class="modal-section flex flex-col gap-4">
        <h4 class="status-label flex items-center gap-2">
          <span class="material-symbols-outlined text-[#656A72] dark:text-white/55 text-base">functions</span>
          Calculation & Rules
        </h4>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <!-- Mode / Amount -->
          <div class="flex flex-col gap-3">
            <p class="status-label">Calculation mode</p>
            
            <div v-if="component.variable_based_on_taxable_salary" class="p-3.5 rounded-[12px] bg-black/[0.03] dark:bg-white/[0.05]">
              <p class="status-label mb-1">Variable tax slabs</p>
              <p class="text-xs text-blue-600 dark:text-blue-400">Calculated automatically based on Income Tax slabs.</p>
            </div>

            <div v-else-if="component.amount_based_on_formula" class="p-3.5 rounded-[12px] bg-black/[0.03] dark:bg-white/[0.05]">
              <p class="status-label mb-1">Formula based</p>
              <p class="text-xs text-purple-600 dark:text-purple-400">Computed via custom Python expression.</p>
            </div>

            <div v-else class="inset-panel">
              <p class="status-label mb-1">Fixed amount</p>
              <p class="modal-title tabular-nums">{{ formatCurrency(component.amount) }}</p>
            </div>
          </div>

          <!-- Condition Expression -->
          <div class="flex flex-col gap-3">
            <p class="status-label">Condition expression</p>
            <div class="inset-panel font-mono text-xs overflow-x-auto min-h-[70px] flex items-center text-[#17181B] dark:text-white/80">
              <code>{{ component.condition || 'No condition specified (always applies)' }}</code>
            </div>
          </div>

          <!-- Formula Code Display -->
          <div v-if="component.amount_based_on_formula" class="col-span-1 md:col-span-2 flex flex-col gap-2">
            <p class="status-label">Formula expression</p>
            <div class="inset-panel font-mono text-xs overflow-x-auto text-[#17181B] dark:text-white/80">
              <code>{{ component.formula || 'No formula defined' }}</code>
            </div>
          </div>
        </div>
      </div>

      <!-- Flexible Benefits Section (If Enabled) -->
      <div v-if="component.is_flexible_benefit" class="modal-section flex flex-col gap-4">
        <h4 class="status-label flex items-center gap-2">
          <span class="material-symbols-outlined text-amber-500 text-base">stars</span>
          Flexible Benefit Settings
        </h4>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <p class="status-label">Max benefit amount (yearly)</p>
            <p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ formatCurrency(component.max_benefit_amount) }}</p>
          </div>

          <div class="col-span-1 md:col-span-2">
            <p class="status-label">Payout method</p>
            <p class="text-[14px] font-semibold text-[#17181B] dark:text-white mt-1">{{ component.payout_method || 'Not specified' }}</p>
          </div>

          <div v-if="component.final_cycle_accrual_payout" class="col-span-1 md:col-span-3">
            <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold tag-amber gap-1.5">
              <span class="material-symbols-outlined text-sm">check_circle</span>
              Payout Unclaimed Amount in Final Payroll Cycle
            </span>
          </div>
        </div>
      </div>

      <!-- Accounts Mapping Section -->
      <div class="modal-section">
        <div class="flex items-center justify-between mb-3">
          <div>
            <h4 class="status-label flex items-center gap-2">
              <span class="material-symbols-outlined text-blue-500 dark:text-blue-400 text-base">account_balance</span>
              Ledger Account Mappings
            </h4>
            <p class="text-xs text-[#5C6169] dark:text-white/65 mt-0.5">Company accounts linked for journal entry postings.</p>
          </div>
          <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold tag-neutral">
            {{ component.accounts ? component.accounts.length : 0 }} Mapped
          </span>
        </div>

        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-black/[0.07] dark:border-white/10">
              <th class="table-th">Company</th>
              <th class="table-th">Account</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!component.accounts || component.accounts.length === 0">
              <td colspan="2" class="py-8 text-center text-[13px] text-[#656A72] dark:text-white/55">
                No company accounts configured for this salary component.
              </td>
            </tr>
            <tr v-for="(acc, idx) in component.accounts" :key="idx" class="border-b last:border-0 border-black/[0.05] dark:border-white/[0.06]">
              <td class="table-td">{{ acc.company }}</td>
              <td class="table-td">{{ acc.account }}</td>
            </tr>
          </tbody>
        </table>
        </div>
      </div>

      <footer class="px-5 py-4 border-t border-black/[0.07] dark:border-white/10 shrink-0">
        <button class="btn-secondary w-full" @click="$emit('close')">Close</button>
      </footer>
    </template>
  </div>
</template>

<script setup>
import { notify, ask } from '@/utils/feedback.js'
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { call } from 'frappe-ui';
import { storeToRefs } from 'pinia';
import { usePayrollStore } from '@/stores/payroll';
import { getErrorMessage } from '@/utils';
import RowActions from '@/components/RowActions.vue';

const props = defineProps({
  id: {
    type: String,
    required: true
  },
  isModal: {
    type: Boolean,
    default: true
  }
});

const emit = defineEmits(['close', 'refresh', 'edit']);

const payrollStore = usePayrollStore();
const { canEditSalaryComponent, canDeleteSalaryComponent } = storeToRefs(payrollStore);

const canEdit = computed(() => canEditSalaryComponent.value);
const canDelete = computed(() => canDeleteSalaryComponent.value);

const loading = ref(true);
const component = ref(null);
const activeActionMenu = ref(false);

function toggleActionMenu() {
  activeActionMenu.value = !activeActionMenu.value;
}

function closeActionMenu() {
  activeActionMenu.value = false;
}

const handleWindowClick = (e) => {
  if (!e.target.closest(".more_vert") && !e.target.closest(".dropdown-menu")) {
    closeActionMenu();
  }
};

const getTypeBadgeBg = (type) => {
  if (type === 'Earning') return 'bg-green-500/[0.10]';
  if (type === 'Deduction') return 'bg-red-50 dark:bg-red-900/20';
  return 'bg-blue-50 dark:bg-blue-900/20';
};

const getTypeTextColor = (type) => {
  if (type === 'Earning') return 'text-green-700 dark:text-green-300';
  if (type === 'Deduction') return 'text-red-600 dark:text-red-400';
  return 'text-blue-600 dark:text-blue-400';
};

const getTypeBadgeClasses = (type) => {
  if (type === 'Earning') return 'tag-emerald';
  if (type === 'Deduction') return 'tag-red';
  return 'tag-accent';
};

const formatCurrency = (amount) => {
  if (amount === null || amount === undefined) return "$0.00";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(amount);
};

const configuredOptionsList = computed(() => {
  if (!component.value) return [];
  const c = component.value;

  const list = [
    { key: 'is_tax_applicable', label: 'Is Tax Applicable', description: 'Include in taxable earnings calculation', enabled: !!c.is_tax_applicable },
    { key: 'depends_on_payment_days', label: 'Depends on Payment Days', description: 'Pro-rate based on employee present/paid days', enabled: !!c.depends_on_payment_days },
    { key: 'deduct_full_tax_on_selected_payroll_date', label: 'Deduct Full Tax on Selected Date', description: 'Deduct full tax for component in single payroll', enabled: !!c.deduct_full_tax_on_selected_payroll_date },
    { key: 'variable_based_on_taxable_salary', label: 'Variable Tax Slabs', description: 'Auto-calculated tax component per tax slabs', enabled: !!c.variable_based_on_taxable_salary },
    { key: 'is_income_tax_component', label: 'Is Income Tax Component', description: 'Considered in Income Tax Deductions report', enabled: !!c.is_income_tax_component },
    { key: 'exempted_from_income_tax', label: 'Exempted from Income Tax', description: 'Deducted from taxable income before tax calculation', enabled: !!c.exempted_from_income_tax },
    { key: 'round_to_the_nearest_integer', label: 'Round to Nearest Integer', description: 'Round component final value', enabled: !!c.round_to_the_nearest_integer },
    { key: 'statistical_component', label: 'Statistical Component', description: 'Reference value without adding to totals', enabled: !!c.statistical_component },
    { key: 'accrual_component', label: 'Accrual Component', description: 'Accrue amounts without adding directly to earnings', enabled: !!c.accrual_component },
    { key: 'do_not_include_in_total', label: 'Do Not Include in Total', description: 'Exclude from total earnings/deductions sum', enabled: !!c.do_not_include_in_total },
    { key: 'do_not_include_in_accounts', label: 'Do Not Include in Accounts', description: 'Exclude from Journal Entries', enabled: !!c.do_not_include_in_accounts },
    { key: 'remove_if_zero_valued', label: 'Remove if Zero Valued', description: 'Hide in payslip when amount is 0', enabled: !!c.remove_if_zero_valued },
    { key: 'arrear_component', label: 'Arrear Component', description: 'Included in arrear calculations', enabled: !!c.arrear_component },
    { key: 'is_flexible_benefit', label: 'Flexible Benefit', description: 'Enable flexi benefit options for employees', enabled: !!c.is_flexible_benefit },
  ];

  return list;
});

const enabledOptionsCount = computed(() => {
  return configuredOptionsList.value.filter(o => o.enabled).length;
});

function handleEdit() {
  closeActionMenu();
  emit('edit', component.value);
}

async function handleDelete() {
  closeActionMenu();
  if (!component.value?.name) return;

  if (await ask(`Are you sure you want to delete the salary component "${component.value.salary_component || component.value.name}"?`)) {
    try {
      await call('arijentek_core.api.payroll.delete_salary_component', { name: component.value.name });
      emit('refresh');
      emit('close');
    } catch (e) {
      console.error('Failed to delete salary component:', e);
      notify(getErrorMessage(e, 'Failed to delete salary component'));
    }
  }
}

async function fetchComponentDetails() {
  loading.value = true;
  try {
    const res = await call('arijentek_core.api.payroll.get_salary_component_details', { name: props.id });
    component.value = res || null;
  } catch (e) {
    console.error("Failed to fetch salary component details:", e);
    component.value = null;
  } finally {
    loading.value = false;
  }
}

watch(() => props.id, (newId) => {
  if (newId) fetchComponentDetails();
});

onMounted(() => {
  window.addEventListener("click", handleWindowClick);
  if (props.id) {
    fetchComponentDetails();
  }
});

onUnmounted(() => {
  window.removeEventListener("click", handleWindowClick);
});
</script>
