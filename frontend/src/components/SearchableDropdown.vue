<template>
  <div class="relative w-full" ref="dropdownContainer">
    <input
      ref="searchInput"
      type="text"
      v-model="searchQuery"
      @click="openAndClear"
      @focus="openAndClear"
      @input="handleInput"
      :placeholder="placeholder"
      :disabled="disabled"
      class="field-input !pr-9"
      :class="{ 'opacity-60 cursor-not-allowed': disabled }"
    >
    <span class="material-symbols-outlined !text-[18px] absolute right-2.5 top-1/2 -translate-y-1/2 text-[#656A72] dark:text-white/60 pointer-events-none">expand_more</span>

    <!-- The POS's menu, so a dropdown is the same object in both products:
         glass panel at 16px, 34px option rows at 10px, and a tick on the row
         that is selected rather than only a tint. -->
    <!-- Teleported and fixed: absolutely placed inside the filter card, the
         table card below painted its sticky header over the top of the list. -->
    <Teleport to="body">
    <div
      v-if="isOpen"
      ref="menuEl"
      class="filter-menu select-menu-pop pointer-events-auto fixed z-[200]"
      :style="menuStyle"
      @pointerdown.stop
      @mousedown.stop
    >
      <button
        v-for="option in filteredOptions"
        :key="getOptionValue(option)"
        type="button"
        @mousedown.prevent="selectOption(option)"
        class="filter-option"
        :class="{ 'is-active': getOptionValue(option) === modelValue }"
      >
        <span class="truncate">{{ getOptionLabel(option) }}</span>
      </button>
      <p v-if="filteredOptions.length === 0" class="px-2.5 py-2 text-[13px] text-[#656A72] dark:text-white/55">
        No results found
      </p>
    </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue';
import { placePopover } from '@/composables/placePopover';

const props = defineProps({
  modelValue: {
    type: [String, Number],
    default: ''
  },
  options: {
    type: Array,
    default: () => []
  },
  placeholder: {
    type: String,
    default: 'Search or select...'
  },
  disabled: {
    type: Boolean,
    default: false
  },
  labelKey: {
    type: String,
    default: null
  },
  valueKey: {
    type: String,
    default: null
  },
  showAllOption: {
    type: Boolean,
    default: false
  },
  allOptionLabel: {
    type: String,
    default: 'All'
  }
});

const emit = defineEmits(['update:modelValue', 'change']);

const isOpen = ref(false);
const searchQuery = ref('');
const dropdownContainer = ref(null);
const searchInput = ref(null);
const menuEl = ref(null);
const menuStyle = ref({});

const place = () => {
  menuStyle.value = placePopover(searchInput.value, menuEl.value);
};

/* Placed twice: once to get the menu into the DOM at a rough spot, then again
   once its real height is known, so the flip-above decision uses it. */
watch(isOpen, async (open) => {
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

const openAndClear = () => {
  if (!isOpen.value) {
    isOpen.value = true;
    searchQuery.value = '';
  }
};

const getOptionLabel = (option) => {
  if (typeof option === 'object' && option !== null) {
    if (props.labelKey) return option[props.labelKey];
    
    if (option.label !== undefined) return option.label;
    if (option.name !== undefined) return option.name;
    
    // Frappe fallback: use the first property ending with '_name'
    for (const key in option) {
      if (key.endsWith('_name')) return option[key];
    }
    
    return option.value || '';
  }
  return option;
};

const getOptionValue = (option) => {
  if (typeof option === 'object' && option !== null) {
    if (props.valueKey) return option[props.valueKey];
    
    if (option.value !== undefined) return option.value;
    if (option.name !== undefined) return option.name;
    
    return option.label || '';
  }
  return option;
};

const effectiveOptions = computed(() => {
  if (props.showAllOption) {
    const allOpt = {};
    if (props.labelKey) allOpt[props.labelKey] = props.allOptionLabel;
    else allOpt.label = props.allOptionLabel;
    
    if (props.valueKey) allOpt[props.valueKey] = '';
    else allOpt.value = '';
    
    return [allOpt, ...props.options];
  }
  return props.options;
});

const updateSearchQueryFromValue = () => {
  if (props.modelValue === null || props.modelValue === undefined) {
    searchQuery.value = '';
    return;
  }
  const selected = effectiveOptions.value.find(opt => getOptionValue(opt) === props.modelValue);
  if (selected) {
    searchQuery.value = getOptionLabel(selected);
  } else {
    searchQuery.value = props.modelValue || '';
  }
};

watch(() => props.modelValue, () => {
  updateSearchQueryFromValue();
});

watch(effectiveOptions, () => {
  updateSearchQueryFromValue();
}, { deep: true });

onMounted(() => {
  updateSearchQueryFromValue();
  document.addEventListener('mousedown', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('mousedown', handleClickOutside);
  window.removeEventListener('resize', place);
  window.removeEventListener('scroll', place, true);
});

const handleClickOutside = (event) => {
  if (menuEl.value && menuEl.value.contains(event.target)) return;
  if (dropdownContainer.value && !dropdownContainer.value.contains(event.target)) {
    isOpen.value = false;
    // On blur, if they typed something but didn't select, reset to currently selected value
    updateSearchQueryFromValue();
  }
};

const filteredOptions = computed(() => {
  const query = searchQuery.value.toLowerCase();
  if (!isOpen.value || !query || query === getOptionLabel(effectiveOptions.value.find(o => getOptionValue(o) === props.modelValue))?.toLowerCase()) {
    return effectiveOptions.value;
  }
  return effectiveOptions.value.filter(option => 
    getOptionLabel(option).toLowerCase().includes(query)
  );
});

/* The list shrinks as you type, so a menu flipped above the field has to move
   down to stay attached to it. */
watch(() => filteredOptions.value.length, async () => {
  if (isOpen.value) {
    await nextTick();
    place();
  }
});

const handleInput = () => {
  isOpen.value = true;
  // If user clears the input completely, we can clear the modelValue
  if (!searchQuery.value) {
    emit('update:modelValue', '');
    emit('change', '');
  }
};

const selectOption = (option) => {
  const val = getOptionValue(option);
  searchQuery.value = getOptionLabel(option);
  emit('update:modelValue', val);
  emit('change', val);
  isOpen.value = false;
  if (searchInput.value) {
    searchInput.value.blur();
  }
};
</script>
