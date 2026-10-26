<template>
	<PortalLayout v-if="!route.meta.guest">
		<router-view />
	</PortalLayout>
	<router-view v-else />
	<ToastHost />
	<ConfirmHost />
</template>

<script setup>
import { useRoute } from "vue-router";
import PortalLayout from "@/components/PortalLayout.vue";
import ToastHost from "@/components/ToastHost.vue";
import ConfirmHost from "@/components/ConfirmHost.vue";

const route = useRoute();
</script>
