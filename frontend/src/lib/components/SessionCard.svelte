<script lang="ts">
	import type { Session } from '$lib/types';
	import { formatDate } from '$lib/utils';

	let { session }: { session: Session } = $props();

	function handleClick() {
		window.location.href = `/session/${session.id}`;
	}
</script>

<button
	onclick={handleClick}
	class="card p-4 hover:shadow-lg transition-all text-left w-full"
>
	<div class="flex items-start justify-between mb-2">
		<span class="badge {session.source === 'claude' ? 'badge-claude' : 'badge-codex'}">
			{session.source}
		</span>
		<span class="text-sm text-gray-500 dark:text-gray-400">
			{formatDate(session.created_at)}
		</span>
	</div>

	<h3 class="text-lg font-medium mb-2 line-clamp-2">
		{session.display || 'No title'}
	</h3>

	{#if session.project}
		<p class="text-sm text-gray-600 dark:text-gray-400 mb-2 truncate">
			{session.project}
		</p>
	{/if}

	<div class="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
		<span>{session.message_count} messages</span>
		{#if session.subagent_count > 0}
			<span>{session.subagent_count} subagents</span>
		{/if}
		{#if session.model}
			<span class="truncate">{session.model}</span>
		{/if}
	</div>
</button>
