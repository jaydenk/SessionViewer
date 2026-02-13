<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { getSession, getSessionMessages, getSessionFiles, exportSessionsPdf } from '$lib/api';
	import { formatDate, renderMarkdown } from '$lib/utils';
	import type { Session, Message, AssociatedFile } from '$lib/types';
	import { fly } from 'svelte/transition';

	let session = $state<Session | null>(null);
	let messages = $state<Message[]>([]);
	let files = $state<AssociatedFile[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let selectedArtifact = $state<AssociatedFile | null>(null);
	let exporting = $state(false);

	const sessionId = $page.params.id;

	async function downloadPdf() {
		try {
			exporting = true;
			const blob = await exportSessionsPdf([sessionId]);
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `${(session?.display || 'session').slice(0, 40)}.pdf`;
			a.click();
			URL.revokeObjectURL(url);
		} catch (err) {
			console.error('PDF export failed:', err);
			alert('PDF export failed. Check console for details.');
		} finally {
			exporting = false;
		}
	}

	onMount(async () => {
		try {
			loading = true;
			[session, messages, files] = await Promise.all([
				getSession(sessionId),
				getSessionMessages(sessionId),
				getSessionFiles(sessionId)
			]);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load session';
		} finally {
			loading = false;
		}
	});

	interface ContentBlock {
		type: 'text' | 'thinking' | 'tool_use' | 'tool_result' | 'function_call' | 'function_call_output' | 'reasoning' | 'unknown';
		text?: string;
		name?: string;
		input?: string;
		output?: string;
		raw?: any;
	}

	function parseContent(content: string): any {
		try {
			return JSON.parse(content);
		} catch {
			return content;
		}
	}

	function parseContentBlocks(content: any): ContentBlock[] {
		if (typeof content === 'string') {
			return content.trim() ? [{ type: 'text', text: content }] : [];
		}
		if (!content) return [];

		const blocks: ContentBlock[] = [];

		// Get the content array — Claude wraps in { content: [...] }, Codex uses { content: [...] } with role
		let items: any[] = [];
		if (content.content && Array.isArray(content.content)) {
			items = content.content;
		} else if (typeof content.content === 'string') {
			// Simple string content (e.g. user message with plain text body)
			const text = content.content.trim();
			if (text) blocks.push({ type: 'text', text });
			return blocks;
		} else if (Array.isArray(content)) {
			items = content;
		}

		// Handle Codex function_call at top level
		if (content.type === 'function_call') {
			blocks.push({
				type: 'function_call',
				name: content.name || content.call_id || 'function',
				input: typeof content.arguments === 'string' ? content.arguments : JSON.stringify(content.arguments, null, 2),
			});
			return blocks;
		}

		// Handle Codex function_call_output at top level
		if (content.type === 'function_call_output') {
			blocks.push({
				type: 'function_call_output',
				output: content.output || JSON.stringify(content, null, 2),
			});
			return blocks;
		}

		if (items.length === 0) {
			// Plain object with no content array — stringify it
			const str = JSON.stringify(content, null, 2);
			if (str !== '{}' && str !== '[]') {
				blocks.push({ type: 'unknown', text: str });
			}
			return blocks;
		}

		for (const item of items) {
			if (!item || typeof item !== 'object') continue;

			switch (item.type) {
				case 'text':
				case 'input_text':
				case 'output_text':
					if (item.text?.trim()) {
						blocks.push({ type: 'text', text: item.text });
					}
					break;
				case 'thinking':
					if (item.thinking?.trim()) {
						blocks.push({ type: 'thinking', text: item.thinking });
					}
					break;
				case 'reasoning':
					if (item.summary?.length) {
						const text = item.summary.map((s: any) => s.text || '').join('\n');
						if (text.trim()) blocks.push({ type: 'reasoning', text });
					}
					break;
				case 'tool_use':
					blocks.push({
						type: 'tool_use',
						name: item.name || 'tool',
						input: typeof item.input === 'string' ? item.input : JSON.stringify(item.input, null, 2),
					});
					break;
				case 'tool_result':
					blocks.push({
						type: 'tool_result',
						output: typeof item.content === 'string'
							? item.content
							: Array.isArray(item.content)
								? item.content.map((c: any) => c.text || JSON.stringify(c)).join('\n')
								: JSON.stringify(item.content, null, 2),
					});
					break;
				default:
					// Include unknown types so they're visible
					if (item.text?.trim()) {
						blocks.push({ type: 'text', text: item.text });
					}
					break;
			}
		}

		return blocks;
	}

	function hasContent(message: Message): boolean {
		const blocks = parseContentBlocks(parseContent(message.content));
		return blocks.length > 0;
	}

	function groupMessages(messages: Message[]): Array<{
		type: string;
		messages: Message[];
		timestamp: string;
	}> {
		const grouped: Array<{ type: string; messages: Message[]; timestamp: string }> = [];
		let currentGroup: Message[] = [];
		let currentType: string | null = null;

		for (const message of messages) {
			if (message.type !== currentType) {
				// Start new group
				if (currentGroup.length > 0) {
					grouped.push({
						type: currentType!,
						messages: currentGroup,
						timestamp: currentGroup[0].timestamp
					});
				}
				currentGroup = [message];
				currentType = message.type;
			} else {
				// Add to current group
				currentGroup.push(message);
			}
		}

		// Add final group
		if (currentGroup.length > 0) {
			grouped.push({
				type: currentType!,
				messages: currentGroup,
				timestamp: currentGroup[0].timestamp
			});
		}

		return grouped;
	}

	function formatTimestamp(timestamp: string): string {
		// Handle UTC timestamps from backend
		const dateStr = timestamp.endsWith('Z') ? timestamp : timestamp + 'Z';
		const date = new Date(dateStr);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

		if (diffDays === 0) {
			return 'Today ' + date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
		} else if (diffDays === 1) {
			return 'Yesterday ' + date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
		} else if (diffDays < 7) {
			return `${diffDays} days ago`;
		} else {
			return date.toLocaleDateString('en-US', {
				month: 'short',
				day: 'numeric',
				hour: '2-digit',
				minute: '2-digit',
				year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
			});
		}
	}

	function getFileIcon(fileType: string): string {
		if (fileType === 'todo') return '📝';
		if (fileType === 'plan') return '📋';
		if (fileType === 'debug') return '🐛';
		if (fileType.startsWith('artifact_')) {
			const filename = fileType.replace('artifact_', '').toLowerCase();
			if (filename.endsWith('.md')) return '📄';
			if (filename.endsWith('.txt')) return '📃';
			if (filename.endsWith('.json')) return '📊';
			if (filename.endsWith('.log')) return '📋';
			return '📎';
		}
		return '📄';
	}

	function getFileDisplayName(fileType: string): string {
		if (fileType === 'todo') return 'TODO.md';
		if (fileType === 'plan') return 'Plan';
		if (fileType === 'debug') return 'Debug Log';
		if (fileType.startsWith('artifact_')) {
			return fileType
				.replace('artifact_', '')
				.replace(/_/g, '/');
		}
		return fileType;
	}

	function isMarkdown(fileType: string): boolean {
		const name = getFileDisplayName(fileType).toLowerCase();
		return name.endsWith('.md') || fileType === 'todo' || fileType === 'plan';
	}

	function getMarkdownArtifacts(): AssociatedFile[] {
		return files.filter((f) => isMarkdown(f.file_type));
	}

	function openArtifact(file: AssociatedFile) {
		selectedArtifact = file;
	}

	function closeArtifact() {
		selectedArtifact = null;
	}

	function getTotalTokens(messages: Message[]): { input: number; output: number } {
		let input = 0;
		let output = 0;
		for (const msg of messages) {
			input += msg.usage_input_tokens || 0;
			output += msg.usage_output_tokens || 0;
		}
		return { input, output };
	}
</script>

<svelte:head>
	<title>{session?.display || 'Session'} - Session Viewer</title>
</svelte:head>

{#if loading}
	<div class="max-w-4xl mx-auto px-4 py-12 text-center">
		<div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
		<p class="mt-2 text-gray-600 dark:text-gray-400">Loading session...</p>
	</div>
{:else if error}
	<div class="max-w-4xl mx-auto px-4 py-12">
		<div class="card p-8 text-center">
			<p class="text-red-600 dark:text-red-400">Error: {error}</p>
			<a href="/" class="mt-4 inline-block text-primary-600 hover:text-primary-700">
				← Back to sessions
			</a>
		</div>
	</div>
{:else if session}
	<div class="max-w-4xl mx-auto px-4 py-8">
		<!-- Back button and actions -->
		<div class="flex items-center justify-between mb-6">
			<a href="/" class="inline-flex items-center text-primary-600 hover:text-primary-700">
				<svg class="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
				</svg>
				Back to sessions
			</a>
			<button
				onclick={downloadPdf}
				disabled={exporting}
				class="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium"
			>
				{#if exporting}
					<div class="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
					Exporting...
				{:else}
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
					</svg>
					Download PDF
				{/if}
			</button>
		</div>

		<!-- Session header -->
		<div class="card p-6 mb-6">
			<div class="flex items-start justify-between mb-4">
				<span class="badge {session.source === 'claude' ? 'badge-claude' : 'badge-codex'}">
					{session.source}
				</span>
				<span class="text-sm text-gray-500 dark:text-gray-400">
					{formatDate(session.created_at)}
				</span>
			</div>

			<h1 class="text-2xl font-bold mb-4 text-gray-900 dark:text-gray-100">
				{session.display || 'Untitled Session'}
			</h1>

			<!-- Quick access to markdown artifacts -->
			{#if getMarkdownArtifacts().length > 0}
				<div class="mb-4 flex flex-wrap gap-2">
					<span class="text-sm text-gray-600 dark:text-gray-400">Quick access:</span>
					{#each getMarkdownArtifacts() as artifact}
						<button
							onclick={() => openArtifact(artifact)}
							class="text-sm px-3 py-1 bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 rounded-full hover:bg-purple-200 dark:hover:bg-purple-800 transition-colors"
						>
							{getFileIcon(artifact.file_type)} {getFileDisplayName(artifact.file_type)}
						</button>
					{/each}
				</div>
			{/if}

			{#if session.project}
				<p class="text-gray-600 dark:text-gray-400 mb-2">
					<strong>Project:</strong> {session.project}
				</p>
			{/if}

			{#if session.cwd}
				<p class="text-gray-600 dark:text-gray-400 mb-2">
					<strong>Working Directory:</strong> <code>{session.cwd}</code>
				</p>
			{/if}

			{#if session.model}
				<p class="text-gray-600 dark:text-gray-400 mb-2">
					<strong>Model:</strong> {session.model}
				</p>
			{/if}

			<div class="flex gap-4 mt-4 text-sm text-gray-600 dark:text-gray-400">
				<span>💬 {session.message_count} messages</span>
				{#if session.subagent_count > 0}
					<span>🤖 {session.subagent_count} subagents</span>
				{/if}
			</div>
		</div>

		<!-- Associated files -->
		{#if files.length > 0}
			<div class="mb-6">
				<h2 class="text-lg font-semibold mb-3 text-gray-900 dark:text-gray-100">
					Associated Files & Artifacts
				</h2>
				<div class="space-y-3">
					{#each files as file}
						<details class="card p-4" open={file.file_type === 'todo' || file.file_type === 'plan'}>
							<summary class="cursor-pointer font-medium flex items-center text-gray-900 dark:text-gray-100">
								{getFileIcon(file.file_type)}
								<span class="ml-2">{getFileDisplayName(file.file_type)}</span>
							</summary>
							<div class="mt-3">
								{#if isMarkdown(file.file_type)}
									<div class="prose prose-sm dark:prose-invert max-w-none prose-headings:font-semibold prose-p:my-2 prose-p:leading-relaxed prose-li:my-1 prose-ul:my-2 prose-ol:my-2 prose-code:bg-gray-100 dark:prose-code:bg-gray-800 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:bg-gray-100 dark:prose-pre:bg-gray-900 prose-pre:p-3 prose-pre:rounded">
										{@html renderMarkdown(file.content)}
									</div>
								{:else}
									<pre class="text-sm overflow-x-auto whitespace-pre-wrap bg-gray-50 dark:bg-gray-900 p-3 rounded text-gray-900 dark:text-gray-100">{file.content}</pre>
								{/if}
							</div>
						</details>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Messages -->
		<div>
			<h2 class="text-lg font-semibold mb-3 text-gray-900 dark:text-gray-100">Messages</h2>
			<div class="space-y-4">
				{#each groupMessages(messages.filter(hasContent)) as group, i (i)}
					{@const tokens = getTotalTokens(group.messages)}
					<div
						class="message-bubble {group.type === 'user' ? 'message-user' : 'message-assistant'}"
						title={tokens.input + tokens.output > 0
							? `Tokens: ${tokens.input} in / ${tokens.output} out`
							: ''}
					>
						<div class="flex items-center justify-between mb-3">
							<span class="font-medium text-gray-900 dark:text-gray-100">
								{group.type === 'user' ? '👤 User' : '🤖 Assistant'}
							</span>
							<span class="text-xs text-gray-500 dark:text-gray-400">
								{formatTimestamp(group.timestamp)}
							</span>
						</div>
						<div class="space-y-3">
							{#each group.messages as message}
								{@const blocks = parseContentBlocks(parseContent(message.content))}
								{#each blocks as block}
									{#if block.type === 'text'}
										<div class="prose dark:prose-invert max-w-none prose-pre:bg-gray-100 dark:prose-pre:bg-gray-900 prose-pre:p-3 prose-pre:rounded prose-code:bg-gray-100 dark:prose-code:bg-gray-800 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-sm">
											{@html renderMarkdown(block.text || '')}
										</div>
									{:else if block.type === 'thinking'}
										<details class="rounded-lg border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-950 overflow-hidden">
											<summary class="px-3 py-2 cursor-pointer text-sm font-medium text-amber-800 dark:text-amber-200 hover:bg-amber-100 dark:hover:bg-amber-900">
												Thinking...
											</summary>
											<div class="px-3 py-2 text-sm whitespace-pre-wrap text-amber-900 dark:text-amber-100 border-t border-amber-200 dark:border-amber-800 max-h-96 overflow-auto">
												{block.text}
											</div>
										</details>
									{:else if block.type === 'reasoning'}
										<details class="rounded-lg border border-purple-300 dark:border-purple-700 bg-purple-50 dark:bg-purple-950 overflow-hidden">
											<summary class="px-3 py-2 cursor-pointer text-sm font-medium text-purple-800 dark:text-purple-200 hover:bg-purple-100 dark:hover:bg-purple-900">
												Reasoning
											</summary>
											<div class="px-3 py-2 text-sm whitespace-pre-wrap text-purple-900 dark:text-purple-100 border-t border-purple-200 dark:border-purple-800 max-h-96 overflow-auto">
												{block.text}
											</div>
										</details>
									{:else if block.type === 'tool_use' || block.type === 'function_call'}
										<details class="rounded-lg border border-green-300 dark:border-green-700 bg-green-50 dark:bg-green-950 overflow-hidden">
											<summary class="px-3 py-2 cursor-pointer text-sm font-medium text-green-800 dark:text-green-200 hover:bg-green-100 dark:hover:bg-green-900">
												Tool: {block.name}
											</summary>
											<pre class="px-3 py-2 text-xs whitespace-pre-wrap text-green-900 dark:text-green-100 border-t border-green-200 dark:border-green-800 max-h-96 overflow-auto bg-transparent">{block.input}</pre>
										</details>
									{:else if block.type === 'tool_result' || block.type === 'function_call_output'}
										<details class="rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-900 overflow-hidden">
											<summary class="px-3 py-2 cursor-pointer text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800">
												Tool Result
											</summary>
											<pre class="px-3 py-2 text-xs whitespace-pre-wrap text-gray-800 dark:text-gray-200 border-t border-gray-200 dark:border-gray-700 max-h-96 overflow-auto bg-transparent">{block.output}</pre>
										</details>
									{:else}
										<pre class="whitespace-pre-wrap text-sm text-gray-900 dark:text-gray-100">{block.text || JSON.stringify(block.raw, null, 2)}</pre>
									{/if}
								{/each}
							{/each}
						</div>
					</div>
				{/each}
			</div>
		</div>
	</div>
{/if}

<!-- Slide-in artifact viewer -->
{#if selectedArtifact}
	<div class="fixed inset-0 z-50 flex items-center justify-end">
		<!-- Backdrop -->
		<button
			class="absolute inset-0 bg-black bg-opacity-50 backdrop-blur-sm"
			onclick={closeArtifact}
			aria-label="Close"
		></button>

		<!-- Slide-in panel -->
		<div
			class="relative bg-white dark:bg-gray-800 w-full max-w-5xl h-full shadow-2xl overflow-auto"
			transition:fly={{ x: 400, duration: 300 }}
		>
			<!-- Header -->
			<div
				class="sticky top-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-4 flex items-center justify-between z-10"
			>
				<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
					{getFileIcon(selectedArtifact.file_type)}
					{getFileDisplayName(selectedArtifact.file_type)}
				</h2>
				<button
					onclick={closeArtifact}
					class="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
					aria-label="Close"
				>
					<svg
						class="w-6 h-6 text-gray-600 dark:text-gray-400"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M6 18L18 6M6 6l12 12"
						/>
					</svg>
				</button>
			</div>

			<!-- Content -->
			<div class="p-8">
				{#if isMarkdown(selectedArtifact.file_type)}
					<div class="prose prose-lg dark:prose-invert max-w-none prose-headings:font-bold prose-h1:text-3xl prose-h1:mb-4 prose-h1:mt-8 prose-h2:text-2xl prose-h2:mb-3 prose-h2:mt-6 prose-h3:text-xl prose-h3:mb-2 prose-h3:mt-4 prose-p:my-4 prose-p:leading-relaxed prose-li:my-2 prose-ul:my-4 prose-ol:my-4 prose-ol:pl-6 prose-ul:pl-6 prose-a:text-blue-600 dark:prose-a:text-blue-400 prose-a:no-underline hover:prose-a:underline prose-code:bg-gray-100 dark:prose-code:bg-gray-800 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-pre:bg-gray-100 dark:prose-pre:bg-gray-900 prose-pre:p-4 prose-pre:rounded-lg prose-table:my-6 prose-th:p-3 prose-td:p-3 prose-blockquote:my-4 prose-blockquote:border-l-4 prose-blockquote:pl-4 prose-hr:my-8 prose-strong:font-semibold">
						{@html renderMarkdown(selectedArtifact.content)}
					</div>
				{:else}
					<pre
						class="text-sm overflow-x-auto whitespace-pre-wrap bg-gray-50 dark:bg-gray-900 p-4 rounded text-gray-900 dark:text-gray-100">{selectedArtifact.content}</pre>
				{/if}
			</div>
		</div>
	</div>
{/if}
