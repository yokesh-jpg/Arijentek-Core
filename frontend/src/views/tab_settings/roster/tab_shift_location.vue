<!--
  tab_shift_location.vue
  Extracted from RosterView.vue — the "shift_location" tab section (line 872–875).
  Delegates to the existing ShiftLocationComponent (tab_settings/shift_location.vue),
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
    <div v-else-if="!canManage" class="table-card">
      <div class="empty-state">
        <span class="material-symbols-outlined !text-[28px] text-[#C4C7CC] dark:text-white/25">lock</span>
        <p class="empty-state-text">You don't have permission to manage shift locations.</p>
      </div>
    </div>

    <ShiftLocationComponent v-else />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRosterStore } from '@/stores/roster';
import ShiftLocationComponent from '@/views/tab_settings/shift_location.vue';

const rosterStore = useRosterStore();
const loading   = ref(true);
const canManage = ref(false);

onMounted(async () => {
  try {
    canManage.value = await rosterStore.checkCanManageShiftLocation();
  } catch {
    canManage.value = false;
  } finally {
    loading.value = false;
  }
});
</script>
