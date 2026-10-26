<template>
  <div class="relative" ref="dropdownContainer">
    <button
      ref="triggerEl"
      type="button"
      @click="showDropdown = !showDropdown"
      class="field-input flex items-center justify-between gap-2 text-left cursor-pointer"
    >
      <span class="truncate">{{ selectedPreset }}</span>
      <!-- Inside the button, not absolutely placed in the container: with the
           inline panel the container grows, and a container-centred chevron
           drifted down into the list. -->
      <span
        class="material-symbols-outlined !text-[18px] text-[#656A72] dark:text-white/60 shrink-0 transition-transform"
        :class="showDropdown ? 'rotate-180' : ''"
        >expand_more</span
      >
    </button>

    <!-- As a popover it is teleported and fixed: absolutely placed inside the
         filter card, the table card below painted its sticky header over the
         top of the list. Inline mode stays in flow (the mobile filter sheet). -->
    <Teleport to="body" :disabled="inline">
    <div
      v-if="showDropdown"
      ref="panelEl"
      class="rounded-[14px] p-2 flex flex-col sm:flex-row gap-2 overflow-y-auto"
      :class="inline ? 'relative mt-2 w-full max-h-[240px] bg-black/[0.03] dark:bg-white/[0.06]' : 'select-menu-pop pointer-events-auto fixed z-[200] min-w-[200px] bg-white dark:bg-surface-2 border border-black/[0.08] dark:border-white/10 shadow-[0_20px_50px_-20px_rgba(0,0,0,.35)]'"
      :style="inline ? null : panelStyle"
      @pointerdown.stop
      @mousedown.stop
    >
      <div class="w-full sm:w-36 flex flex-col gap-0.5 shrink-0">
        <button
          v-for="preset in presets"
          :key="preset"
          type="button"
          @click="applyPreset(preset)"
          class="w-full text-left px-3 py-2 rounded-[10px] text-[13px] font-medium transition-colors"
          :class="selectedPreset === preset ? 'bg-accent/10 text-accent dark:text-accent-light' : 'text-gray-900 dark:text-white hover:bg-black/[0.04] dark:hover:bg-white/[0.06]'"
        >
          {{ preset }}
        </button>
      </div>

      <div
        v-if="selectedPreset === 'Custom Range'"
        class="w-full sm:w-48 shrink-0 pt-2 sm:pt-0 sm:pl-2 border-t sm:border-t-0 sm:border-l border-black/[0.06] dark:border-white/[0.08] flex flex-col gap-2"
      >
        <div>
          <label class="field-label !mb-1">From</label>
          <DateField v-model="internalFromDate" />
        </div>
        <div>
          <label class="field-label !mb-1">To</label>
          <DateField v-model="internalToDate" :min="internalFromDate" />
        </div>
        <button type="button" @click="applyCustomRange" class="btn-primary w-full">
          Apply range
        </button>
      </div>
    </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue';
import DateField from './DateField.vue'
import { placePopover } from '@/composables/placePopover';

const props = defineProps({
  fromDate: { type: String, default: '' },
  toDate: { type: String, default: '' },
  preset: { type: String, default: 'All Time' },
  /* Render the presets in flow instead of as a popover. A popover inside the
     mobile filter sheet can only ever be clipped by the sheet's own scroll
     box — there is no room above or below it. */
  inline: { type: Boolean, default: false }
});

const emit = defineEmits(['update:fromDate', 'update:toDate', 'update:preset', 'change']);

const showDropdown = ref(false);
const selectedPreset = ref(props.preset);
const internalFromDate = ref(props.fromDate);
const internalToDate = ref(props.toDate);
const dropdownContainer = ref(null);
const triggerEl = ref(null);
const panelEl = ref(null);
const panelStyle = ref({});

const place = () => {
  if (props.inline) return;
  panelStyle.value = placePopover(triggerEl.value, panelEl.value);
};

/* Placed twice: the first pass puts the panel in the DOM, the second uses its
   real height to decide whether it opens above or below. */
watch(showDropdown, async (open) => {
  if (open) {
    await nextTick();
    place();
    await nextTick();
    place();
    window.addEventListener('resize', place);
    window.addEventListener('scroll', place, true);
  } else {
    window.removeEventListener('resize', place);
    window.removeEventListener('scroll', place, true);
  }
});

const presets = [
  'All Time',
  'Today',
  'Yesterday',
  'Last 7 Days',
  'Last 30 Days',
  'This Month',
  'Last Month',
  'Custom Range',
];

watch(() => props.preset, (newVal) => {
  selectedPreset.value = newVal;
});
watch(() => props.fromDate, (newVal) => {
  internalFromDate.value = newVal;
});
watch(() => props.toDate, (newVal) => {
  internalToDate.value = newVal;
});

function applyPreset(preset) {
  selectedPreset.value = preset;

  if (preset === 'Custom Range') {
    // Just switch to custom mode, don't emit yet. Wait for Apply Range button.
    // The panel grows a second column, so it is re-placed to stay on screen.
    nextTick(place);
    return;
  }
  
  const now = new Date();
  let from = '';
  let to = '';
  
  const formatDate = (date) => {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  };

  if (preset === 'Today') {
    from = formatDate(now);
    to = formatDate(now);
  } else if (preset === 'Yesterday') {
    const yesterday = new Date(now);
    yesterday.setDate(now.getDate() - 1);
    from = formatDate(yesterday);
    to = formatDate(yesterday);
  } else if (preset === 'Last 7 Days') {
    const last7 = new Date(now);
    last7.setDate(now.getDate() - 7);
    from = formatDate(last7);
    to = formatDate(now);
  } else if (preset === 'Last 30 Days') {
    const last30 = new Date(now);
    last30.setDate(now.getDate() - 30);
    from = formatDate(last30);
    to = formatDate(now);
  } else if (preset === 'This Month') {
    const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
    const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    from = formatDate(firstDay);
    to = formatDate(lastDay);
  } else if (preset === 'Last Month') {
    const firstDay = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    const lastDay = new Date(now.getFullYear(), now.getMonth(), 0);
    from = formatDate(firstDay);
    to = formatDate(lastDay);
  }

  internalFromDate.value = from;
  internalToDate.value = to;
  showDropdown.value = false;
  
  emitUpdates();
}

watch(internalFromDate, (newFrom) => {
  if (newFrom && (!internalToDate.value || internalToDate.value < newFrom)) {
    internalToDate.value = newFrom;
  }
});

function applyCustomRange() {
  if (internalFromDate.value && internalToDate.value && internalToDate.value < internalFromDate.value) {
    internalToDate.value = internalFromDate.value;
  }
  showDropdown.value = false;
  emitUpdates();
}

function emitUpdates() {
  emit('update:preset', selectedPreset.value);
  emit('update:fromDate', internalFromDate.value);
  emit('update:toDate', internalToDate.value);
  emit('change', { preset: selectedPreset.value, fromDate: internalFromDate.value, toDate: internalToDate.value });
}

function handleClickOutside(event) {
  if (panelEl.value && panelEl.value.contains(event.target)) return;
  if (dropdownContainer.value && !dropdownContainer.value.contains(event.target)) {
    showDropdown.value = false;
  }
}

onMounted(() => {
  document.addEventListener('mousedown', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('mousedown', handleClickOutside);
  window.removeEventListener('resize', place);
  window.removeEventListener('scroll', place, true);
});
</script>
