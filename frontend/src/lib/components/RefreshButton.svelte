<script lang="ts">
	import { refreshIndex, getIndexStatus } from '$lib/api';

	let refreshing = $state(false);

	async function handleRefresh() {
		if (refreshing) return;
		refreshing = true;

		try {
			const result = await refreshIndex();
			if (result.status === 'already_running' || result.status === 'started') {
				// Poll until indexing completes
				await pollUntilDone();
			}
		} catch (error) {
			console.error('Failed to trigger refresh:', error);
		} finally {
			refreshing = false;
			window.dispatchEvent(new CustomEvent('sessions-refreshed'));
		}
	}

	async function pollUntilDone() {
		const maxAttempts = 60;
		for (let i = 0; i < maxAttempts; i++) {
			await new Promise((r) => setTimeout(r, 1000));
			try {
				const status = await getIndexStatus();
				if (!status.is_indexing) return;
			} catch {
				// ignore poll errors
			}
		}
	}
</script>

<button
	onclick={handleRefresh}
	class="p-2 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
	aria-label="Refresh sessions"
	disabled={refreshing}
>
	<svg
		class="w-5 h-5"
		class:animate-spin={refreshing}
		fill="none"
		stroke="currentColor"
		viewBox="0 0 24 24"
		stroke-width="2"
	>
		<path
			stroke-linecap="round"
			stroke-linejoin="round"
			d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
		/>
	</svg>
</button>
