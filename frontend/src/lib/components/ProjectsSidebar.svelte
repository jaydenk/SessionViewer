<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { getProjects } from '$lib/api';

	interface Props {
		onNavigate?: () => void;
	}

	let { onNavigate }: Props = $props();

	let projects = $state<string[]>([]);
	let loading = $state(true);
	let collapsed = $state(false);
	let selectedProject = $state<string | null>(null);

	onMount(async () => {
		try {
			projects = await getProjects();
		} catch (error) {
			console.error('Failed to load projects:', error);
		} finally {
			loading = false;
		}
	});

	function getProjectName(projectPath: string): string {
		if (projectPath === '(No Project)') return 'Ungrouped';
		// Get the last part of the path (working directory name)
		const parts = projectPath.split('/');
		return parts[parts.length - 1] || projectPath;
	}

	function navigateToProject(project: string) {
		if (project === selectedProject) {
			// Deselect - show all
			selectedProject = null;
			goto('/');
		} else {
			// Select project
			selectedProject = project;
			const projectParam = project === '(No Project)' ? '' : project;
			goto(`/?project=${encodeURIComponent(projectParam)}`);
		}
		onNavigate?.();
	}

	// Update selected project from URL on mount and navigation
	$effect(() => {
		if ($page.url.searchParams.has('project')) {
			const urlProject = $page.url.searchParams.get('project');
			selectedProject = urlProject || '(No Project)';
		} else {
			selectedProject = null;
		}
	});
</script>

<aside class="sidebar" class:collapsed>
	<button
		class="collapse-btn"
		onclick={() => (collapsed = !collapsed)}
		aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
	>
		<svg
			xmlns="http://www.w3.org/2000/svg"
			width="16"
			height="16"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			stroke-width="2"
		>
			{#if collapsed}
				<polyline points="9 18 15 12 9 6"></polyline>
			{:else}
				<polyline points="15 18 9 12 15 6"></polyline>
			{/if}
		</svg>
	</button>

	{#if !collapsed}
		<div class="sidebar-content">
			<div class="sidebar-header">
				<h2>Projects</h2>
			</div>

			<div class="projects-list">
				{#if loading}
					<div class="loading">Loading...</div>
				{:else if projects.length === 0}
					<div class="empty">No projects found</div>
				{:else}
					{#each projects as project (project)}
						<button
							class="project-item"
							class:active={selectedProject === project}
							onclick={() => navigateToProject(project)}
						>
							<div class="project-icon">
								{#if project === '(No Project)'}
									📂
								{:else}
									📁
								{/if}
							</div>
							<div class="project-name">{getProjectName(project)}</div>
						</button>
					{/each}
				{/if}
			</div>
		</div>
	{/if}
</aside>

<style>
	.sidebar {
		position: relative;
		width: 280px;
		min-width: 280px;
		height: 100%;
		background: var(--color-bg-secondary, #f9fafb);
		border-right: 1px solid var(--color-border, #e5e7eb);
		display: flex;
		flex-direction: column;
		transition: width 0.2s ease, min-width 0.2s ease;
	}

	:global(.dark) .sidebar {
		background: rgb(31, 41, 55);
		border-right-color: rgb(55, 65, 81);
	}

	.sidebar.collapsed {
		width: 48px;
		min-width: 48px;
	}

	.collapse-btn {
		position: absolute;
		top: 12px;
		right: 12px;
		width: 28px;
		height: 28px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: transparent;
		border: none;
		color: rgb(107, 114, 128);
		z-index: 1;
		border-radius: 4px;
		transition: all 0.15s ease;
		cursor: pointer;
	}

	:global(.dark) .collapse-btn {
		color: rgb(156, 163, 175);
	}

	.collapse-btn:hover {
		color: rgb(17, 24, 39);
		background: rgba(0, 0, 0, 0.05);
	}

	:global(.dark) .collapse-btn:hover {
		color: rgb(243, 244, 246);
		background: rgba(255, 255, 255, 0.05);
	}

	.collapsed .collapse-btn {
		right: 50%;
		transform: translateX(50%);
	}

	.sidebar-content {
		display: flex;
		flex-direction: column;
		height: 100%;
		overflow: hidden;
	}

	.sidebar-header {
		padding: 16px 16px 12px;
		border-bottom: 1px solid var(--color-border, #e5e7eb);
	}

	:global(.dark) .sidebar-header {
		border-bottom-color: rgb(55, 65, 81);
	}

	.sidebar-header h2 {
		font-size: 0.875rem;
		font-weight: 600;
		color: rgb(107, 114, 128);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin: 0;
	}

	:global(.dark) .sidebar-header h2 {
		color: rgb(156, 163, 175);
	}

	.projects-list {
		flex: 1;
		overflow-y: auto;
		padding: 8px;
	}

	.loading,
	.empty {
		padding: 32px 16px;
		text-align: center;
		color: rgb(107, 114, 128);
		font-size: 0.875rem;
	}

	:global(.dark) .loading,
	:global(.dark) .empty {
		color: rgb(156, 163, 175);
	}

	.empty {
		font-style: italic;
	}

	.project-item {
		display: flex;
		align-items: center;
		gap: 12px;
		width: 100%;
		padding: 10px 12px;
		margin-bottom: 2px;
		border-radius: 8px;
		text-decoration: none;
		color: inherit;
		transition: all 0.15s ease;
		border: 1px solid transparent;
		background: transparent;
		cursor: pointer;
		text-align: left;
	}

	.project-item:hover {
		background: rgba(0, 0, 0, 0.05);
		border-color: var(--color-border, #e5e7eb);
	}

	:global(.dark) .project-item:hover {
		background: rgba(255, 255, 255, 0.05);
		border-color: rgb(55, 65, 81);
	}

	.project-item.active {
		background: rgb(243, 244, 246);
		border-color: rgb(147, 51, 234);
	}

	:global(.dark) .project-item.active {
		background: rgb(55, 65, 81);
		border-color: rgb(168, 85, 247);
	}

	.project-icon {
		font-size: 1.25rem;
		flex-shrink: 0;
		width: 24px;
		text-align: center;
	}

	.project-name {
		font-size: 0.875rem;
		line-height: 1.4;
		color: rgb(17, 24, 39);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	:global(.dark) .project-name {
		color: rgb(243, 244, 246);
	}

	@media (max-width: 768px) {
		.sidebar {
			width: 100%;
			min-width: 100%;
			border-right: none;
		}

		.sidebar.collapsed {
			display: none;
		}

		.collapse-btn {
			display: none;
		}

		.sidebar-header {
			padding: 16px;
		}
	}
</style>
