<template>
	<!-- The POS list footer (Purchases, Vendors): the range on the left; rows
	     per page, Previous, the page count and Next on the right. Worded
	     buttons rather than bare chevrons, so the control says what it does. -->
	<div class="table-foot">
		<span class="text-xs text-[#5C6169] dark:text-white/55 tabular-nums">
			Showing {{ first }}–{{ last }} of {{ total }}
		</span>
		<div class="flex flex-wrap items-center gap-x-4 gap-y-2">
			<div v-if="pageSize != null" class="flex items-center gap-2">
				<span class="text-xs text-[#5C6169] dark:text-white/55">Per page</span>
				<SelectField
					:model-value="pageSize"
					:options="sizes"
					:block="false"
					trigger-class="page-size-select"
					aria-label="Rows per page"
					@update:model-value="setSize"
				/>
			</div>
			<div class="flex items-center gap-1">
				<button type="button" class="pager-btn" :disabled="page <= 1" @click="$emit('update:page', page - 1)">Previous</button>
				<span class="px-2 text-xs text-[#5C6169] dark:text-white/55 tabular-nums">Page {{ page }} of {{ pages }}</span>
				<button type="button" class="pager-btn" :disabled="page >= pages" @click="$emit('update:page', page + 1)">Next</button>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from 'vue'
import SelectField from './SelectField.vue'

const props = defineProps({
	page: { type: Number, required: true },
	total: { type: Number, default: 0 },
	/* Leave null where a list has a fixed page size: the selector is hidden. */
	pageSize: { type: [Number, String], default: null },
	/* Only needed with no pageSize; otherwise derived. */
	perPage: { type: Number, default: 10 },
	sizes: { type: Array, default: () => [10, 20, 50] },
})
const emit = defineEmits(['update:page', 'update:pageSize'])

const size = computed(() => Number(props.pageSize ?? props.perPage) || 10)
const pages = computed(() => Math.max(1, Math.ceil(props.total / size.value)))
const first = computed(() => (props.total ? (props.page - 1) * size.value + 1 : 0))
const last = computed(() => Math.min(props.page * size.value, props.total))

function setSize(v) {
	emit('update:pageSize', Number(v))
	emit('update:page', 1)
}
</script>
