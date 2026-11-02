<template>
	<PortalLayout v-if="auth.isLoggedIn && !route.meta.guest">
		<router-view v-slot="{ Component }">
			<keep-alive :include="['AttendanceView', 'RosterView', 'LeaveView', 'ExpenseView', 'IssuesView', 'SettingsView']">
				<component :is="Component" />
			</keep-alive>
		</router-view>
	</PortalLayout>
	<router-view v-else />
	<ToastHost />
	<ConfirmHost />
</template>

<script setup>
import { useRoute } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import PortalLayout from "@/components/PortalLayout.vue";
import ToastHost from "@/components/ToastHost.vue";
import ConfirmHost from "@/components/ConfirmHost.vue";

const route = useRoute();
const auth = useAuthStore();
</script>
