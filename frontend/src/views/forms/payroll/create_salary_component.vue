<template>
  <Teleport to="body">
    <Dialog :options="{ size: '5xl' }" v-model="show">
      <template #body>
        <div class="modal-panel flex flex-col overflow-hidden max-h-[85vh]">
          <!-- Custom Header -->
          <header class="modal-header shrink-0 sticky top-0 z-20 flex justify-between items-center">
            <div>
              <h1 class="modal-title">
                {{ isEdit ? 'Edit salary component' : 'New salary component' }}
              </h1>
              <p class="text-xs font-medium text-[#5C6169] dark:text-white/65">
                {{ isEdit ? (formData.name || editId) : 'Fill in the details below to configure salary component' }}
              </p>
            </div>
            <button @click="show = false" class="p-2 -mr-2 rounded-[12px] text-[#5C6169] hover:text-[#17181B] dark:text-white/65 dark:hover:text-white/80 hover:bg-black/[0.04] dark:hover:bg-white/[0.08] transition-colors">
              <span class="material-symbols-outlined">close</span>
            </button>
          </header>

          <!-- Tabs Header -->
          <div class="px-4 pt-4 shrink-0 bg-white dark:bg-white/[0.06]">
            <div class="flex border-b border-black/[0.07] dark:border-white/10 px-2 overflow-x-auto gap-1">
              <button 
                @click="activeTab = 'overview'"
                :class="[ 'px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap', activeTab === 'overview' ? 'border-accent/30 text-accent dark:text-accent-light font-semibold' : 'border-transparent text-[#5C6169] dark:text-white/65 hover:text-[#17181B]' ]"
              >
                Overview <span class="text-red-500 dark:text-red-400">*</span>
              </button>

              <button 
                @click="activeTab = 'condition'"
                :class="[ 'px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap', activeTab === 'condition' ? 'border-accent/30 text-accent dark:text-accent-light font-semibold' : 'border-transparent text-[#5C6169] dark:text-white/65 hover:text-[#17181B]' ]"
              >
                Condition & Formula
              </button>

              <button 
                v-if="formData.type === 'Earning' && !formData.statistical_component"
                @click="activeTab = 'flexible_benefits'"
                :class="[ 'px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap', activeTab === 'flexible_benefits' ? 'border-accent/30 text-accent dark:text-accent-light font-semibold' : 'border-transparent text-[#5C6169] dark:text-white/65 hover:text-[#17181B]' ]"
              >
                Flexible Benefits
              </button>

              <button 
                v-if="!formData.statistical_component && formData.type !== 'Employer Contribution'"
                @click="activeTab = 'accounts'"
                :class="[ 'px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap', activeTab === 'accounts' ? 'border-accent/30 text-accent dark:text-accent-light font-semibold' : 'border-transparent text-[#5C6169] dark:text-white/65 hover:text-[#17181B]' ]"
              >
                Accounts ({{ formData.accounts ? formData.accounts.length : 0 }})
              </button>
            </div>
          </div>

          <!-- Tab Content -->
          <div class="p-6 overflow-y-auto max-h-[55vh] md:max-h-[60vh]">
            <div v-if="loadingDetails" class="py-12 flex justify-center items-center">
              <div class="w-8 h-8 border-2 border-accent/30 border-t-transparent rounded-full animate-spin"></div>
            </div>

            <template v-else>
              <!-- OVERVIEW TAB -->
              <div v-if="activeTab === 'overview'" class="flex flex-col gap-6">
                <!-- Basic Details Grid -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div class="flex flex-col gap-1.5">
                    <label class="field-label">
                      Name <span class="text-red-500 dark:text-red-400">*</span>
                    </label>
                    <input 
                      v-model="formData.salary_component" 
                      type="text" 
                      placeholder="e.g. Basic Salary, HRA" 
                      class="field-input"
                    />
                    <p v-if="errors.salary_component" class="field-error text-red-500 dark:text-red-400 mt-0.5">{{ errors.salary_component }}</p>
                  </div>

                  <div class="flex flex-col gap-1.5">
                    <label class="field-label">
                      Abbreviation <span class="text-red-500 dark:text-red-400">*</span>
                    </label>
                    <input 
                      v-model="formData.salary_component_abbr" 
                      type="text" 
                      placeholder="e.g. BS, HRA, TDS" 
                      class="field-input uppercase"
                    />
                    <p v-if="errors.salary_component_abbr" class="field-error text-red-500 dark:text-red-400 mt-0.5">{{ errors.salary_component_abbr }}</p>
                  </div>

                  <div class="flex flex-col gap-1.5">
                    <label class="field-label">
                      Type <span class="text-red-500 dark:text-red-400">*</span>
                    </label>
                    <SearchableDropdown 
                      v-model="formData.type" 
                      :options="['Earning', 'Deduction', 'Employer Contribution']" 
                      placeholder="Select type" 
                      @change="handleTypeChange"
                    />
                    <p v-if="errors.type" class="field-error text-red-500 dark:text-red-400 mt-0.5">{{ errors.type }}</p>
                  </div>

                  <div class="flex flex-col gap-1.5 justify-end">
                    <label class="flex items-center gap-2 cursor-pointer py-2">
                      <input 
                        type="checkbox" 
                        v-model="formData.disabled" 
                        :true-value="1" 
                        :false-value="0"
                        class="w-4 h-4 rounded text-accent dark:text-accent-light focus:ring-accent/20 border-black/[0.09] dark:border-white/10" 
                      />
                      <span class="text-sm font-semibold text-[#17181B] dark:text-white/80">Disabled</span>
                    </label>
                  </div>

                  <div class="flex flex-col gap-1.5 md:col-span-2">
                    <label class="field-label">Description</label>
                    <textarea 
                      v-model="formData.description" 
                      rows="2" 
                      placeholder="Brief component description..." 
                      class="px-3 py-2 bg-black/[0.02] dark:bg-white/[0.04] text-[#17181B] dark:text-white/90 border border-black/[0.07] dark:border-white/10 rounded-[12px] text-sm focus:outline-none focus:border-accent/30 transition-all resize-none"
                    ></textarea>
                  </div>
                </div>

                <div class="h-px bg-black/[0.08] dark:bg-white/10 my-1"></div>

                <!-- Component Configurations / Flags -->
                <div>
                  <h3 class="field-label mb-4">Behavior & Tax Options</h3>
                  <div class="inset-panel grid grid-cols-1 md:grid-cols-2 gap-4">
                    
                    <!-- Earning Specific -->
                    <template v-if="formData.type === 'Earning'">
                      <label class="flex items-start gap-2.5 cursor-pointer">
                        <input type="checkbox" v-model="formData.is_tax_applicable" :true-value="1" :false-value="0" class="mt-0.5 w-4 h-4 rounded text-accent dark:text-accent-light focus:ring-accent/20 border-black/[0.09] dark:border-white/10">
                        <div class="flex flex-col">
                          <span class="text-sm font-medium text-[#17181B] dark:text-white/80">Is Tax Applicable</span>
                          <span class="text-xs text-[#5C6169] dark:text-white/65">Include in taxable earnings calculation</span>
                        </div>
                      </label>

                      <label v-if="formData.is_tax_applicable" class="flex items-start gap-2.5 cursor-pointer">
                        <input type="checkbox" v-model="formData.deduct_full_tax_on_selected_payroll_date" :true-value="1" :false-value="0" class="mt-0.5 w-4 h-4 rounded text-accent dark:text-accent-light focus:ring-accent/20 border-black/[0.09] dark:border-white/10">
                        <div class="flex flex-col">
                          <span class="text-sm font-medium text-[#17181B] dark:text-white/80">Deduct Full Tax on Selected Payroll Date</span>
                          <span class="text-xs text-[#5C6169] dark:text-white/65">Deduct full tax for this component in single payroll</span>
                        </div>
                      </label>
                    </template>

                    <!-- Deduction Specific -->
                    <template v-if="formData.type === 'Deduction'">
                      <label class="flex items-start gap-2.5 cursor-pointer">
                        <input type="checkbox" v-model="formData.variable_based_on_taxable_salary" :true-value="1" :false-value="0" @change="handleVariableTaxChange" class="mt-0.5 w-4 h-4 rounded text-accent dark:text-accent-light focus:ring-accent/20 border-black/[0.09] dark:border-white/10">
                        <div class="flex flex-col">
                          <span class="text-sm font-medium text-[#17181B] dark:text-white/80">Variable Based On Taxable Salary</span>
                          <span class="text-xs text-[#5C6169] dark:text-white/65">Auto-calculated tax component per tax slabs</span>
                        </div>
                      </label>

                      <label class="flex items-start gap-2.5 cursor-pointer">
                        <input type="checkbox" v-model="formData.is_income_tax_component" :true-value="1" :false-value="0" class="mt-0.5 w-4 h-4 rounded text-accent dark:text-accent-light focus:ring-accent/20 border-black/[0.09] dark:border-white/10">
                        <div class="flex flex-col">
                          <span class="text-sm font-medium text-[#17181B] dark:text-white/80">Is Income Tax Component</span>
                          <span class="text-xs text-[#5C6169] dark:text-white/65">Considered in Income Tax Deductions report</span>
                        </div>
                      </label>

                      <label v-if="!formData.variable_based_on_taxable_salary" class="flex items-start gap-2.5 cursor-pointer">
                        <input type="checkbox" v-model="formData.exempted_from_income_tax" :true-value="1" :false-value="0" class="mt-0.5 w-4 h-4 rounded text-accent dark:text-accent-light focus:ring-accent/20 border-black/[0.09] dark:border-white/10">
                        <div class="flex flex-col">
                          <span class="text-sm font-medium text-[#17181B] dark:text-white/80">Exempted from Income Tax</span>
                          <span class="text-xs text-[#5C6169] dark:text-white/65">Deducted from taxable income before calculating tax</span>
                        </div>
                      </label>
                    </template>

                    <!-- Common Flags -->
                    <label class="flex items-start gap-2.5 cursor-pointer">
                      <input type="checkbox" v-model="formData.depends_on_payment_days" :true-value="1" :false-value="0" class="mt-0.5 w-4 h-4 rounded text-accent dark:text-accent-light focus:ring-accent/20 border-black/[0.09] dark:border-white/10">
                      <div class="flex flex-col">
                        <span class="text-sm font-medium text-[#17181B] dark:text-white/80">Depends on Payment Days</span>
                        <span class="text-xs text-[#5C6169] dark:text-white/65">Pro-rate based on employee present/paid days</span>
                      </div>
                    </label>

                    <label class="flex items-start gap-2.5 cursor-pointer">
                      <input type="checkbox" v-model="formData.round_to_the_nearest_integer" :true-value="1" :false-value="0" class="mt-0.5 w-4 h-4 rounded text-accent dark:text-accent-light focus:ring-accent/20 border-black/[0.09] dark:border-white/10">
                      <div class="flex flex-col">
                        <span class="text-sm font-medium text-[#17181B] dark:text-white/80">Round to the Nearest Integer</span>
                        <span class="text-xs text-[#5C6169] dark:text-white/65">Round component final value</span>
                      </div>
                    </label>

                    <template v-if="formData.type !== 'Employer Contribution'">
                      <label class="flex items-start gap-2.5 cursor-pointer">
                        <input type="checkbox" v-model="formData.statistical_component" :true-value="1" :false-value="0" class="mt-0.5 w-4 h-4 rounded text-accent dark:text-accent-light focus:ring-accent/20 border-black/[0.09] dark:border-white/10">
                        <div class="flex flex-col">
                          <span class="text-sm font-medium text-[#17181B] dark:text-white/80">Statistical Component</span>
                          <span class="text-xs text-[#5C6169] dark:text-white/65">Reference value without adding to earnings/deductions</span>
                        </div>
                      </label>

                      <label v-if="formData.type === 'Earning'" class="flex items-start gap-2.5 cursor-pointer">
                        <input type="checkbox" v-model="formData.accrual_component" :true-value="1" :false-value="0" :disabled="formData.is_flexible_benefit === 1" class="mt-0.5 w-4 h-4 rounded text-accent dark:text-accent-light focus:ring-accent/20 border-black/[0.09] dark:border-white/10 disabled:opacity-50">
                        <div class="flex flex-col">
                          <span class="text-sm font-medium text-[#17181B] dark:text-white/80">Accrual Component</span>
                          <span class="text-xs text-[#5C6169] dark:text-white/65">Accrue amounts without adding directly to earnings</span>
                        </div>
                      </label>

                      <label class="flex items-start gap-2.5 cursor-pointer">
                        <input type="checkbox" v-model="formData.do_not_include_in_total" :true-value="1" :false-value="0" @change="handleDoNotIncludeTotalChange" class="mt-0.5 w-4 h-4 rounded text-accent dark:text-accent-light focus:ring-accent/20 border-black/[0.09] dark:border-white/10">
                        <div class="flex flex-col">
                          <span class="text-sm font-medium text-[#17181B] dark:text-white/80">Do Not Include in Total</span>
                          <span class="text-xs text-[#5C6169] dark:text-white/65">Exclude from total earnings/deductions sum</span>
                        </div>
                      </label>

                      <label v-if="formData.do_not_include_in_total" class="flex items-start gap-2.5 cursor-pointer">
                        <input type="checkbox" v-model="formData.do_not_include_in_accounts" :true-value="1" :false-value="0" class="mt-0.5 w-4 h-4 rounded text-accent dark:text-accent-light focus:ring-accent/20 border-black/[0.09] dark:border-white/10">
                        <div class="flex flex-col">
                          <span class="text-sm font-medium text-[#17181B] dark:text-white/80">Do Not Include in Accounting Entries</span>
                          <span class="text-xs text-[#5C6169] dark:text-white/65">Exclude from Journal Entries</span>
                        </div>
                      </label>

                      <label v-if="!formData.statistical_component" class="flex items-start gap-2.5 cursor-pointer">
                        <input type="checkbox" v-model="formData.remove_if_zero_valued" :true-value="1" :false-value="0" class="mt-0.5 w-4 h-4 rounded text-accent dark:text-accent-light focus:ring-accent/20 border-black/[0.09] dark:border-white/10">
                        <div class="flex flex-col">
                          <span class="text-sm font-medium text-[#17181B] dark:text-white/80">Remove if Zero Valued</span>
                          <span class="text-xs text-[#5C6169] dark:text-white/65">Hide in payslip when amount is 0</span>
                        </div>
                      </label>

                      <label class="flex items-start gap-2.5 cursor-pointer">
                        <input type="checkbox" v-model="formData.arrear_component" :true-value="1" :false-value="0" @change="handleArrearChange" :disabled="formData.variable_based_on_taxable_salary === 1" class="mt-0.5 w-4 h-4 rounded text-accent dark:text-accent-light focus:ring-accent/20 border-black/[0.09] dark:border-white/10 disabled:opacity-50">
                        <div class="flex flex-col">
                          <span class="text-sm font-medium text-[#17181B] dark:text-white/80">Arrear Component</span>
                          <span class="text-xs text-[#5C6169] dark:text-white/65">Included in arrear calculations</span>
                        </div>
                      </label>
                    </template>
                  </div>
                </div>
              </div>

              <!-- CONDITION & FORMULA TAB -->
              <div v-else-if="activeTab === 'condition'" class="flex flex-col gap-6">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <!-- Form side -->
                  <div class="flex flex-col gap-4">
                    <div class="flex flex-col gap-1.5">
                      <label class="field-label">Condition</label>
                      <textarea 
                        v-model="formData.condition" 
                        rows="3" 
                        placeholder="e.g. base < 10000 or employment_type == 'Intern'" 
                        class="px-3 py-2 bg-black/[0.02] dark:bg-white/[0.04] text-[#17181B] dark:text-white/90 font-mono border border-black/[0.07] dark:border-white/10 rounded-[12px] text-sm focus:outline-none focus:border-accent/30 transition-all resize-none"
                      ></textarea>
                      <p class="text-xs text-[#5C6169] dark:text-white/65">Python expression evaluated to determine if this component applies.</p>
                    </div>

                    <div class="flex flex-col gap-2 pt-2">
                      <label class="flex items-center gap-2 cursor-pointer">
                        <input type="checkbox" v-model="formData.amount_based_on_formula" :true-value="1" :false-value="0" class="w-4 h-4 rounded text-accent dark:text-accent-light focus:ring-accent/20 border-black/[0.09] dark:border-white/10">
                        <span class="text-sm font-semibold text-[#17181B] dark:text-white/80">Amount based on formula</span>
                      </label>
                    </div>

                    <div v-if="formData.amount_based_on_formula" class="flex flex-col gap-1.5">
                      <label class="field-label">Formula</label>
                      <textarea 
                        v-model="formData.formula" 
                        rows="4" 
                        placeholder="e.g. base * 0.2 or BS * 0.1" 
                        class="px-3 py-2 bg-black/[0.02] dark:bg-white/[0.04] text-[#17181B] dark:text-white/90 font-mono border border-black/[0.07] dark:border-white/10 rounded-[12px] text-sm focus:outline-none focus:border-accent/30 transition-all resize-none"
                      ></textarea>
                      <p class="text-xs text-[#5C6169] dark:text-white/65">Python expression to calculate amount.</p>
                    </div>

                    <div v-else class="flex flex-col gap-1.5">
                      <label class="field-label">Amount</label>
                      <input 
                        v-model.number="formData.amount" 
                        type="number" 
                        step="0.01" 
                        placeholder="0.00" 
                        class="field-input"
                      />
                    </div>
                  </div>

                  <!-- Help documentation side -->
                  <div class="inset-panel flex flex-col gap-3">
                    <div class="flex items-center gap-2 font-semibold text-[#17181B] dark:text-white/80 text-sm">
                      <span class="material-symbols-outlined text-accent dark:text-accent-light text-base">help_outline</span>
                      Formula & Condition Syntax Guide
                    </div>
                    <ul class="space-y-1.5 list-disc pl-4">
                      <li>Use <code class="bg-black/[0.08] dark:bg-white/[0.08] px-1 py-0.5 rounded text-[#17181B] dark:text-white/90">base</code> for employee base salary.</li>
                      <li>Use Salary Component abbreviations directly, e.g. <code class="bg-black/[0.08] dark:bg-white/[0.08] px-1 py-0.5 rounded text-[#17181B] dark:text-white/90">BS</code> for Basic Salary.</li>
                      <li>Use employee details fields, e.g. <code class="bg-black/[0.08] dark:bg-white/[0.08] px-1 py-0.5 rounded text-[#17181B] dark:text-white/90">employment_type</code>, <code class="bg-black/[0.08] dark:bg-white/[0.08] px-1 py-0.5 rounded text-[#17181B] dark:text-white/90">branch</code>.</li>
                      <li>Use Salary Slip fields like <code class="bg-black/[0.08] dark:bg-white/[0.08] px-1 py-0.5 rounded text-[#17181B] dark:text-white/90">payment_days</code> or <code class="bg-black/[0.08] dark:bg-white/[0.08] px-1 py-0.5 rounded text-[#17181B] dark:text-white/90">leave_without_pay</code>.</li>
                    </ul>

                    <div class="font-semibold text-[#17181B] dark:text-white/80 mt-2">Examples:</div>
                    <div class="space-y-2">
                      <div class="bg-white dark:bg-white/[0.06] p-2 rounded-[12px] border border-black/[0.07] dark:border-white/10">
                        <p class="font-semibold text-[#17181B] dark:text-white/80">1. Basic Salary based on base:</p>
                        <p class="font-mono text-xs text-accent dark:text-accent-light">Condition: base &lt; 10000</p>
                        <p class="font-mono text-xs text-accent dark:text-accent-light">Formula: base * 0.2</p>
                      </div>
                      <div class="bg-white dark:bg-white/[0.06] p-2 rounded-[12px] border border-black/[0.07] dark:border-white/10">
                        <p class="font-semibold text-[#17181B] dark:text-white/80">2. HRA based on Basic Salary (BS):</p>
                        <p class="font-mono text-xs text-accent dark:text-accent-light">Condition: BS &gt; 2000</p>
                        <p class="font-mono text-xs text-accent dark:text-accent-light">Formula: BS * 0.1</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- FLEXIBLE BENEFITS TAB -->
              <div v-else-if="activeTab === 'flexible_benefits'" class="flex flex-col gap-6">
                <div class="inset-panel flex flex-col gap-4">
                  <label class="flex items-start gap-2.5 cursor-pointer">
                    <input 
                      type="checkbox" 
                      v-model="formData.is_flexible_benefit" 
                      :true-value="1" 
                      :false-value="0"
                      @change="handleFlexibleBenefitChange" 
                      class="mt-0.5 w-4 h-4 rounded text-accent dark:text-accent-light focus:ring-accent/20 border-black/[0.09] dark:border-white/10" 
                    />
                    <div class="flex flex-col">
                      <span class="text-sm font-semibold text-[#17181B] dark:text-white/80">Is Flexible Benefit</span>
                      <span class="text-xs text-[#5C6169] dark:text-white/65">Enable flexi benefit options for employees</span>
                    </div>
                  </label>

                  <template v-if="formData.is_flexible_benefit">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                      <div class="flex flex-col gap-1.5">
                        <label class="field-label">
                          Max Benefit Amount (Yearly)
                        </label>
                        <input 
                          v-model.number="formData.max_benefit_amount" 
                          type="number" 
                          step="0.01" 
                          placeholder="0.00" 
                          class="px-3 py-2 bg-white dark:bg-white/[0.06] text-[#17181B] dark:text-white/90 border border-black/[0.07] dark:border-white/10 rounded-[12px] text-sm focus:outline-none focus:border-accent/30 transition-all"
                        />
                        <p class="text-xs text-[#5C6169] dark:text-white/65">Max benefit amount assignable to any employee yearly.</p>
                      </div>

                      <div class="flex flex-col gap-1.5">
                        <label class="field-label">
                          Payout Method <span class="text-red-500 dark:text-red-400">*</span>
                        </label>
                        <SearchableDropdown 
                          v-model="formData.payout_method" 
                          :options="payoutMethodOptions" 
                          placeholder="Select payout method" 
                          @change="handlePayoutMethodChange"
                        />
                        <p v-if="errors.payout_method" class="field-error text-red-500 dark:text-red-400 mt-0.5">{{ errors.payout_method }}</p>
                      </div>
                    </div>

                    <div v-if="formData.payout_method === 'Accrue per cycle, pay only on claim'" class="pt-2">
                      <label class="flex items-start gap-2.5 cursor-pointer">
                        <input 
                          type="checkbox" 
                          v-model="formData.final_cycle_accrual_payout" 
                          :true-value="1" 
                          :false-value="0" 
                          class="mt-0.5 w-4 h-4 rounded text-accent dark:text-accent-light focus:ring-accent/20 border-black/[0.09] dark:border-white/10" 
                        />
                        <div class="flex flex-col">
                          <span class="text-sm font-medium text-[#17181B] dark:text-white/80">Payout Unclaimed Amount in Final Payroll Cycle</span>
                          <span class="text-xs text-[#5C6169] dark:text-white/65">Automatically payout remaining balance at end of year</span>
                        </div>
                      </label>
                    </div>
                  </template>
                </div>
              </div>

              <!-- ACCOUNTS TAB -->
              <div v-else-if="activeTab === 'accounts'" class="flex flex-col gap-4">
                <div class="flex items-center justify-between">
                  <div>
                    <h3 class="text-sm font-semibold text-[#17181B] dark:text-white/80">Company Account Mappings</h3>
                    <p class="text-xs text-[#5C6169] dark:text-white/65">Specify ledger accounts per company for payroll journal postings.</p>
                  </div>
                  <button 
                    @click="addAccountRow" 
                    type="button"
                    class="btn-secondary"
                  >
                    <span class="material-symbols-outlined text-sm">add</span> Add Row
                  </button>
                </div>

                <div class="border border-black/[0.07] dark:border-white/10 rounded-[12px] overflow-hidden">
                  <table class="w-full text-left border-collapse text-sm">
                    <thead>
                      <tr class="border-b border-black/[0.07] dark:border-white/10">
                        <th class="table-th">Company</th>
                        <th class="table-th">Account</th>
                        <th class="table-th w-16 !text-center">Action</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-black/[0.05] dark:divide-white/[0.06] bg-white dark:bg-surface-1">
                      <tr v-for="(row, idx) in formData.accounts" :key="idx" class="hover:bg-black/[0.03] dark:hover:bg-white/[0.05]">
                        <td class="px-4 py-2.5">
                          <SearchableDropdown 
                            v-model="row.company" 
                            :options="companyOptions" 
                            labelKey="company_name" 
                            valueKey="name" 
                            placeholder="Select company"
                          />
                        </td>
                        <td class="px-4 py-2.5">
                          <SearchableDropdown 
                            v-model="row.account" 
                            :options="getFilteredAccountOptions(row.company)" 
                            labelKey="account_name" 
                            valueKey="name" 
                            placeholder="Select account"
                          />
                        </td>
                        <td class="px-4 py-2.5 text-center">
                          <button 
                            @click="removeAccountRow(idx)" 
                            type="button"
                            class="p-1.5 text-red-400 hover:text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-[12px] transition-colors" 
                            title="Remove Row"
                          >
                            <span class="material-symbols-outlined text-sm">delete</span>
                          </button>
                        </td>
                      </tr>
                      <tr v-if="!formData.accounts || formData.accounts.length === 0">
                        <td colspan="3" class="px-4 py-6 text-center text-[#656A72] dark:text-white/60 text-xs">
                          No account mappings configured. Click "Add Row" to assign company accounts.
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </template>
          </div>

          <!-- Actions Footer -->
          <footer class="flex flex-col p-4 border-t border-black/[0.07] dark:border-white/10 bg-white dark:bg-white/[0.06] shrink-0">
            <p v-if="submitError" class="text-sm text-red-500 dark:text-red-400 font-medium text-center mb-3">{{ submitError }}</p>
            <div class="flex justify-end gap-3">
              <button 
                class="btn-secondary" 
                @click="show = false"
                :disabled="submitting"
              >
                Cancel
              </button>
              <button 
                class="btn-primary flex items-center gap-2 disabled:opacity-70" 
                @click="handleSave"
                :disabled="submitting || loadingDetails"
              >
                <span v-if="submitting" class="material-symbols-outlined text-[18px] animate-spin">progress_activity</span>
                <span v-else class="material-symbols-outlined text-[18px]">save</span>
                {{ submitting ? 'Saving…' : 'Save component' }}
              </button>
            </div>
          </footer>
        </div>
      </template>
    </Dialog>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { Dialog, call } from 'frappe-ui';
import SearchableDropdown from '../../../components/SearchableDropdown.vue';
import { getErrorMessage } from '@/utils';

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  editData: {
    type: Object,
    default: null
  },
  editId: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['update:modelValue', 'save']);

const show = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
});

const isEdit = computed(() => !!props.editData || !!props.editId);

const activeTab = ref('overview');
const loadingDetails = ref(false);
const submitting = ref(false);
const submitError = ref('');
const errors = ref({});

const companyOptions = ref([]);
const allAccounts = ref([]);

const payoutMethodOptions = [
  'Accrue and payout at end of payroll period',
  'Accrue per cycle, pay only on claim',
  'Allow claim for full benefit amount'
];

const getInitialFormData = () => ({
  name: '',
  salary_component: '',
  salary_component_abbr: '',
  type: 'Earning',
  description: '',
  disabled: 0,
  is_tax_applicable: 1,
  depends_on_payment_days: 1,
  deduct_full_tax_on_selected_payroll_date: 0,
  variable_based_on_taxable_salary: 0,
  is_income_tax_component: 0,
  exempted_from_income_tax: 0,
  round_to_the_nearest_integer: 0,
  statistical_component: 0,
  accrual_component: 0,
  do_not_include_in_total: 0,
  do_not_include_in_accounts: 0,
  remove_if_zero_valued: 1,
  arrear_component: 0,
  condition: '',
  amount_based_on_formula: 0,
  formula: '',
  amount: 0,
  is_flexible_benefit: 0,
  max_benefit_amount: 0,
  payout_method: '',
  final_cycle_accrual_payout: 0,
  accounts: []
});

const formData = ref(getInitialFormData());

const getFilteredAccountOptions = (company) => {
  if (!company) return allAccounts.value;
  return allAccounts.value.filter(a => a.company === company);
};

const addAccountRow = () => {
  if (!formData.value.accounts) formData.value.accounts = [];
  formData.value.accounts.push({ company: '', account: '' });
};

const removeAccountRow = (idx) => {
  formData.value.accounts.splice(idx, 1);
};

const handleTypeChange = (newType) => {
  if (newType === 'Earning') {
    formData.value.is_tax_applicable = 1;
    formData.value.variable_based_on_taxable_salary = 0;
  } else if (newType === 'Deduction') {
    formData.value.is_tax_applicable = 0;
    formData.value.is_flexible_benefit = 0;
    formData.value.accrual_component = 0;
  }
};

const handleVariableTaxChange = () => {
  if (formData.value.variable_based_on_taxable_salary) {
    formData.value.formula = '';
    formData.value.condition = '';
    formData.value.amount_based_on_formula = 0;
    formData.value.statistical_component = 0;
    formData.value.do_not_include_in_total = 0;
    formData.value.do_not_include_in_accounts = 0;
    formData.value.depends_on_payment_days = 0;
    formData.value.arrear_component = 0;
  }
};

const handleDoNotIncludeTotalChange = () => {
  if (!formData.value.do_not_include_in_total) {
    formData.value.do_not_include_in_accounts = 0;
  }
};

const handleArrearChange = () => {
  if (formData.value.arrear_component) {
    formData.value.depends_on_payment_days = 1;
  }
};

const handleFlexibleBenefitChange = () => {
  if (formData.value.is_flexible_benefit) {
    formData.value.formula = '';
    formData.value.condition = '';
    formData.value.amount_based_on_formula = 0;
    formData.value.statistical_component = 0;
    formData.value.do_not_include_in_total = 0;
    formData.value.do_not_include_in_accounts = 0;
    formData.value.depends_on_payment_days = 0;
    formData.value.amount = 0;
  } else {
    formData.value.payout_method = '';
  }
};

const handlePayoutMethodChange = (newVal) => {
  if (formData.value.is_flexible_benefit) {
    if (['Accrue and payout at end of payroll period', 'Accrue per cycle, pay only on claim'].includes(newVal)) {
      formData.value.accrual_component = 1;
    } else {
      formData.value.accrual_component = 0;
    }
  }
};

const fetchOptions = async () => {
  try {
    const res = await call('arijentek_core.api.payroll.get_salary_component_options');
    if (res) {
      companyOptions.value = res.companies || [];
      allAccounts.value = res.accounts || [];
    }
  } catch (e) {
    console.error('Failed to fetch salary component options:', e);
  }
};

watch(show, async (newVal) => {
  if (newVal) {
    activeTab.value = 'overview';
    submitError.value = '';
    errors.value = {};
    formData.value = getInitialFormData();
    
    fetchOptions();

    const targetName = props.editData?.name || props.editId;
    if (targetName) {
      loadingDetails.value = true;
      try {
        const details = await call('arijentek_core.api.payroll.get_salary_component_details', { name: targetName });
        if (details) {
          formData.value = { ...getInitialFormData(), ...details };
          if (!formData.value.accounts) formData.value.accounts = [];
        }
      } catch (err) {
        console.error('Failed to fetch salary component details:', err);
        submitError.value = getErrorMessage(err, 'Failed to load component details');
      } finally {
        loadingDetails.value = false;
      }
    }
  }
});

const validate = () => {
  errors.value = {};
  let isValid = true;
  let firstErrorTab = null;

  if (!formData.value.salary_component) {
    errors.value.salary_component = 'Component Name is mandatory';
    isValid = false;
    firstErrorTab = firstErrorTab || 'overview';
  }

  if (!formData.value.salary_component_abbr) {
    errors.value.salary_component_abbr = 'Abbreviation is mandatory';
    isValid = false;
    firstErrorTab = firstErrorTab || 'overview';
  }

  if (!formData.value.type) {
    errors.value.type = 'Type is mandatory';
    isValid = false;
    firstErrorTab = firstErrorTab || 'overview';
  }

  if (formData.value.is_flexible_benefit && !formData.value.payout_method) {
    errors.value.payout_method = 'Payout Method is mandatory when Flexible Benefit is enabled';
    isValid = false;
    firstErrorTab = firstErrorTab || 'flexible_benefits';
  }

  if (firstErrorTab) {
    activeTab.value = firstErrorTab;
  }

  return isValid;
};

const handleSave = async () => {
  submitError.value = '';
  if (!validate()) return;

  submitting.value = true;
  try {
    const res = await call('arijentek_core.api.payroll.save_salary_component', { doc: formData.value });
    if (res) {
      emit('save', { ...formData.value, name: res });
      show.value = false;
    }
  } catch (err) {
    console.error('Failed to save salary component:', err);
    submitError.value = getErrorMessage(err, 'Failed to save salary component');
  } finally {
    submitting.value = false;
  }
};
</script>
