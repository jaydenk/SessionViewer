<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { sessions } from '$lib/stores/sessions';
	import { filters } from '$lib/stores/filters';
	import SessionCard from '$lib/components/SessionCard.svelte';
	import { debounce, renderMarkdown } from '$lib/utils';
	import { getProjectFiles } from '$lib/api';
	import type { AssociatedFile } from '$lib/types';
	import { fly } from 'svelte/transition';

	let searchInput = $state('');
	let projectFiles = $state<AssociatedFile[]>([]);
	let loadingProjectFiles = $state(false);
	let selectedProjectFile = $state<AssociatedFile | null>(null);

	// Sync URL params with filters
	$effect(() => {
		if ($page.url.searchParams.has('project')) {
			const urlProject = $page.url.searchParams.get('project') || null;
			if (urlProject !== $filters.project) {
				filters.setProject(urlProject);
				loadSessions();
				loadProjectFiles(urlProject);
			}
		} else {
			projectFiles = [];
		}
	});

	// Debounced search
	const handleSearch = debounce((value: string) => {
		filters.setSearch(value || null);
		loadSessions();
	}, 500);

	$effect(() => {
		handleSearch(searchInput);
	});

	async function loadSessions() {
		await sessions.load($filters);
	}

	async function loadProjectFiles(projectPath: string | null) {
		if (!projectPath) {
			projectFiles = [];
			return;
		}

		try {
			loadingProjectFiles = true;
			projectFiles = await getProjectFiles(projectPath);
		} catch (error) {
			console.error('Failed to load project files:', error);
			projectFiles = [];
		} finally {
			loadingProjectFiles = false;
		}
	}

	function handleSourceChange(source: string) {
		const currentSource = $filters.source;
		if (currentSource === source) {
			filters.setSource(null);
		} else {
			filters.setSource(source);
		}
		loadSessions();
	}

	function clearFilters() {
		filters.reset();
		searchInput = '';
		loadSessions();
	}

	function getProjectName(projectPath: string): string {
		if (!projectPath || projectPath === '(No Project)') return 'Ungrouped Sessions';
		const parts = projectPath.split('/');
		return parts[parts.length - 1] || projectPath;
	}

	function getProjectFileName(fileType: string): string {
		return fileType.replace('project_', '');
	}

	function getFileIcon(fileType: string): string {
		const name = fileType.toLowerCase();
		if (name.includes('todo')) return '✓';
		if (name.includes('readme')) return '📖';
		if (name.includes('claude')) return '🤖';
		if (name.includes('agent')) return '🤖';
		if (name.includes('audit')) return '🔍';
		if (name.includes('notes')) return '📝';
		return '📄';
	}

	function isMarkdown(fileName: string): boolean {
		return fileName.toLowerCase().endsWith('.md');
	}

	function openProjectFile(file: AssociatedFile) {
		selectedProjectFile = file;
	}

	function closeProjectFile() {
		selectedProjectFile = null;
	}

	onMount(() => {
		loadSessions();

		const onRefreshed = () => {
			loadSessions();
			if ($filters.project) loadProjectFiles($filters.project);
		};
		window.addEventListener('sessions-refreshed', onRefreshed);
		return () => window.removeEventListener('sessions-refreshed', onRefreshed);
	});
</script>

<svelte:head>
	<title>Session Viewer</title>
</svelte:head>

<div class="px-6 py-8">
	<!-- Page header -->
	{#if $filters.project}
		<div class="mb-6">
			<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">
				{getProjectName($filters.project)}
			</h1>
			<p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
				Sessions for this project
			</p>
		</div>
	{:else}
		<div class="mb-6">
			<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">All Sessions</h1>
			<p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
				Browse all your AI assistant conversations
			</p>
		</div>
	{/if}

	<!-- Project Files -->
	{#if $filters.project && projectFiles.length > 0}
		<div class="mb-6 card p-4">
			<h2 class="text-lg font-semibold mb-3 text-gray-900 dark:text-gray-100">
				Project Documentation
			</h2>
			<div class="flex flex-wrap gap-2">
				{#each projectFiles as file}
					<button
						onclick={() => openProjectFile(file)}
						class="text-sm px-3 py-1.5 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-lg hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors flex items-center gap-2"
					>
						<span>{getFileIcon(file.file_type)}</span>
						<span>{getProjectFileName(file.file_type)}</span>
					</button>
				{/each}
			</div>
		</div>
	{/if}

	<!-- Filters -->
	<div class="mb-6 card p-4">
		<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
			<!-- Source filter -->
			<div>
				<label class="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300"
					>Source</label
				>
				<div class="flex gap-2">
					<button
						onclick={() => handleSourceChange('claude')}
						class="flex-1 px-3 py-2 rounded-lg border transition-colors {$filters.source ===
						'claude'
							? 'bg-purple-100 dark:bg-purple-900 border-purple-500'
							: 'border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'}"
					>
						Claude
					</button>
					<button
						onclick={() => handleSourceChange('codex')}
						class="flex-1 px-3 py-2 rounded-lg border transition-colors {$filters.source ===
						'codex'
							? 'bg-blue-100 dark:bg-blue-900 border-blue-500'
							: 'border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'}"
					>
						Codex
					</button>
				</div>
			</div>

			<!-- Search -->
			<div class="md:col-span-2">
				<label for="search" class="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300"
					>Search</label
				>
				<input
					id="search"
					type="text"
					bind:value={searchInput}
					placeholder="Search sessions..."
					class="input"
				/>
			</div>
		</div>

		{#if $filters.source || $filters.search}
			<div class="mt-4">
				<button
					onclick={clearFilters}
					class="text-sm text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300"
				>
					Clear filters
				</button>
			</div>
		{/if}
	</div>

	<!-- Results -->
	{#if $sessions.loading}
		<div class="text-center py-12">
			<div
				class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"
			></div>
			<p class="mt-2 text-gray-600 dark:text-gray-400">Loading sessions...</p>
		</div>
	{:else if $sessions.error}
		<div class="card p-8 text-center">
			<p class="text-red-600 dark:text-red-400">Error: {$sessions.error}</p>
		</div>
	{:else if $sessions.data}
		<div class="mb-4 flex items-center justify-between">
			<p class="text-sm text-gray-600 dark:text-gray-400">
				Showing {$sessions.data.sessions.length} of {$sessions.data.total} sessions
			</p>
		</div>

		{#if $sessions.data.sessions.length === 0}
			<div class="card p-12 text-center">
				<p class="text-lg text-gray-600 dark:text-gray-400">No sessions found</p>
				<p class="mt-2 text-sm text-gray-500 dark:text-gray-500">
					Try adjusting your filters or select a different project
				</p>
			</div>
		{:else}
			<div class="space-y-3">
				{#each $sessions.data.sessions as session (session.id)}
					<SessionCard {session} />
				{/each}
			</div>

			<!-- Pagination -->
			{#if $sessions.data.total_pages > 1}
				<div class="mt-6 flex items-center justify-center gap-2">
					<button
						onclick={() => {
							filters.setPage($filters.page - 1);
							loadSessions();
						}}
						disabled={$filters.page === 1}
						class="btn btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
					>
						Previous
					</button>

					<span class="px-4 py-2 text-gray-700 dark:text-gray-300">
						Page {$filters.page} of {$sessions.data.total_pages}
					</span>

					<button
						onclick={() => {
							filters.setPage($filters.page + 1);
							loadSessions();
						}}
						disabled={$filters.page === $sessions.data.total_pages}
						class="btn btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
					>
						Next
					</button>
				</div>
			{/if}
		{/if}
	{/if}
</div>

<!-- Slide-in project file viewer -->
{#if selectedProjectFile}
	<div class="fixed inset-0 z-50 flex items-center justify-end">
		<!-- Backdrop -->
		<button
			class="absolute inset-0 bg-black bg-opacity-50 backdrop-blur-sm"
			onclick={closeProjectFile}
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
					{getFileIcon(selectedProjectFile.file_type)}
					{getProjectFileName(selectedProjectFile.file_type)}
				</h2>
				<button
					onclick={closeProjectFile}
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
				{#if isMarkdown(getProjectFileName(selectedProjectFile.file_type))}
					<div class="prose prose-lg dark:prose-invert max-w-none prose-headings:font-bold prose-h1:text-3xl prose-h1:mb-4 prose-h1:mt-8 prose-h2:text-2xl prose-h2:mb-3 prose-h2:mt-6 prose-h3:text-xl prose-h3:mb-2 prose-h3:mt-4 prose-p:my-4 prose-p:leading-relaxed prose-li:my-2 prose-ul:my-4 prose-ol:my-4 prose-ol:pl-6 prose-ul:pl-6 prose-a:text-blue-600 dark:prose-a:text-blue-400 prose-a:no-underline hover:prose-a:underline prose-code:bg-gray-100 dark:prose-code:bg-gray-800 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-pre:bg-gray-100 dark:prose-pre:bg-gray-900 prose-pre:p-4 prose-pre:rounded-lg prose-table:my-6 prose-th:p-3 prose-td:p-3 prose-blockquote:my-4 prose-blockquote:border-l-4 prose-blockquote:pl-4 prose-hr:my-8 prose-strong:font-semibold">
						{@html renderMarkdown(selectedProjectFile.content)}
					</div>
				{:else}
					<pre
						class="text-sm overflow-x-auto whitespace-pre-wrap bg-gray-50 dark:bg-gray-900 p-4 rounded text-gray-900 dark:text-gray-100">{selectedProjectFile.content}</pre>
				{/if}
			</div>
		</div>
	</div>
{/if}
