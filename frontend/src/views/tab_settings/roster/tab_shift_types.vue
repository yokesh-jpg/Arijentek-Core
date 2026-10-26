<!--
  tab_shift_types.vue
  Extracted from RosterView.vue — the "shift_types" tab section (line 877–880).
  Delegates to the existing ShiftTypesComponent (tab_settings/shift_types.vue),
  exactly as done in RosterView.vue. Wraps in permission guard using rosterStore.
-->
<template>
  <div class="tab-fill">
    <div v-if="loading" class="table-card">
      <div class="empty-state">
        <span class="material-symbols-outlined !text-[28px] text-accent dark:text-accent-light animate-spin">progress_activity</span>
        <p class="empty-state-text">Loading…</p>
      </div>
    </div>

    <!-- A missing permission is not an error, so it reads as an empty state
         rather than the red alert panel that used to sit here. -->
    <div v-else-if="!canView" class="table-card">
      <div class="empty-state">
        <span class="material-symbols-outlined !text-[28px] text-[#C4C7CC] dark:text-white/25">lock</span>
        <p class="empty-state-text">You don't have permission to view shift types.</p>
      </div>
    </div>

    <ShiftTypesComponent v-else />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { createResource } from 'frappe-ui';
import ShiftTypesComponent from '@/views/tab_settings/shift_types.vue';

const loading = ref(true);
const canView  = ref(false);

onMounted(async () => {
  try {
    // Same check used in RosterView.vue onMounted (line 2785-2792)
    const res = createResource({
      url: 'arijentek_core.api.roster.can_view_shift_type',
      auto: false,
    });
    canView.value = await res.fetch();
  } catch {
    canView.value = false;
  } finally {
    loading.value = false;
  }
});
</script>
