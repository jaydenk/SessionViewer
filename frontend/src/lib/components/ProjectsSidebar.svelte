<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { getProjects } from '$lib/api';
	import type { ProjectInfo } from '$lib/types';

	interface Props {
		onNavigate?: () => void;
	}

	let { onNavigate }: Props = $props();

	let projects = $state<ProjectInfo[]>([]);
	let loading = $state(true);
	let collapsed = $state(false);
	let selectedProject = $state<string | null>(null);
	let sortMode = $state<'alpha' | 'recent'>('alpha');

	// Pinned projects state backed by localStorage
	let pinnedProjects = $state<Set<string>>(new Set(
		JSON.parse(localStorage.getItem('pinnedProjects') || '[]')
	));

	function togglePin(project: string) {
		const next = new Set(pinnedProjects);
		if (next.has(project)) {
			next.delete(project);
		} else {
			next.add(project);
		}
		pinnedProjects = next;
		localStorage.setItem('pinnedProjects', JSON.stringify([...next]));
	}

	function isPinned(project: string): boolean {
		return pinnedProjects.has(project);
	}

	function getProjectName(projectPath: string): string {
		if (projectPath === '(No Project)') return 'Ungrouped';
		const parts = projectPath.split('/');
		return parts[parts.length - 1] || projectPath;
	}

	function getDateBucket(dateStr: string): string {
		// API returns UTC timestamps without timezone suffix — force UTC interpretation
		const utcStr = dateStr.endsWith('Z') || dateStr.includes('+') ? dateStr : dateStr + 'Z';
		const date = new Date(utcStr);
		const now = new Date();

		// Compare against local day boundaries
		const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
		const yesterdayStart = new Date(todayStart.getTime() - 86_400_000);
		const weekAgo = new Date(todayStart.getTime() - 7 * 86_400_000);
		const monthAgo = new Date(todayStart.getTime() - 30 * 86_400_000);
		const yearAgo = new Date(todayStart.getTime() - 365 * 86_400_000);

		if (date >= todayStart) return 'Today';
		if (date >= yesterdayStart) return 'Yesterday';
		if (date >= weekAgo) return 'This Week';
		if (date >= monthAgo) return 'This Month';
		if (date >= yearAgo) return 'This Year';
		return 'Older';
	}

	interface ProjectGroup {
		label: string;
		items: ProjectInfo[];
	}

	let groupedProjects = $derived.by((): ProjectGroup[] => {
		const pinned = projects
			.filter(p => pinnedProjects.has(p.project))
			.sort((a, b) => a.project.localeCompare(b.project));
		const unpinned = projects.filter(p => !pinnedProjects.has(p.project));

		let groups: ProjectGroup[] = [];

		if (pinned.length > 0) {
			groups.push({ label: 'Pinned', items: pinned });
		}

		const sorted = [...unpinned];

		if (sortMode === 'recent') {
			sorted.sort((a, b) => new Date(b.last_activity + 'Z').getTime() - new Date(a.last_activity + 'Z').getTime());
			const bucketOrder = ['Today', 'Yesterday', 'This Week', 'This Month', 'This Year', 'Older'];
			const buckets = new Map<string, ProjectInfo[]>();
			for (const item of sorted) {
				const bucket = getDateBucket(item.last_activity);
				if (!buckets.has(bucket)) buckets.set(bucket, []);
				buckets.get(bucket)!.push(item);
			}
			groups.push(...bucketOrder
				.filter(b => buckets.has(b))
				.map(b => ({ label: b, items: buckets.get(b)! })));
		} else {
			sorted.sort((a, b) => getProjectName(a.project).localeCompare(getProjectName(b.project)));
			const letterGroups = new Map<string, ProjectInfo[]>();
			for (const item of sorted) {
				const name = getProjectName(item.project);
				const letter = name[0]?.toUpperCase() || '#';
				const key = /[A-Z]/.test(letter) ? letter : '#';
				if (!letterGroups.has(key)) letterGroups.set(key, []);
				letterGroups.get(key)!.push(item);
			}
			const sortedEntries = Array.from(letterGroups.entries()).sort((a, b) => a[0].localeCompare(b[0]));
			groups.push(...sortedEntries.map(([label, items]) => ({ label, items })));
		}

		return groups;
	});

	async function loadProjects() {
		try {
			loading = true;
			projects = await getProjects();
		} catch (error) {
			console.error('Failed to load projects:', error);
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		loadProjects();

		const onRefreshed = () => loadProjects();
		window.addEventListener('sessions-refreshed', onRefreshed);
		return () => window.removeEventListener('sessions-refreshed', onRefreshed);
	});

	function navigateToProject(project: string) {
		if (project === selectedProject) {
			selectedProject = null;
			goto('/');
		} else {
			selectedProject = project;
			const projectParam = project === '(No Project)' ? '' : project;
			goto(`/?project=${encodeURIComponent(projectParam)}`);
		}
		onNavigate?.();
	}

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
				<div class="sort-controls">
					<button
						class="sort-btn"
						class:active={sortMode === 'alpha'}
						onclick={() => (sortMode = 'alpha')}
						aria-label="Sort alphabetically"
						title="Sort A-Z"
					>
						<!-- A-Z with arrow -->
						<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<text x="1" y="15" font-size="12" font-weight="600" fill="currentColor" stroke="none" font-family="system-ui">A</text>
							<path d="M14 7l3-3 3 3" />
							<path d="M17 4v16" />
						</svg>
					</button>
					<button
						class="sort-btn"
						class:active={sortMode === 'recent'}
						onclick={() => (sortMode = 'recent')}
						aria-label="Sort by recent activity"
						title="Sort by recent"
					>
						<!-- Clock with arrow -->
						<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<circle cx="10" cy="12" r="7" />
							<polyline points="10 8 10 12 13 13.5" />
							<path d="M20 7l2-3 2 3" />
							<path d="M22 4v10" />
						</svg>
					</button>
				</div>
			</div>

			<div class="projects-list">
				{#if loading}
					<div class="loading">Loading...</div>
				{:else if projects.length === 0}
					<div class="empty">No projects found</div>
				{:else}
					{#each groupedProjects as group (group.label)}
						<div class="group">
							<div class="group-heading">{group.label}</div>
							{#each group.items as info (info.project)}
								<!-- svelte-ignore a11y_no_static_element_interactions -->
							<div
								class="project-item"
								class:active={selectedProject === info.project}
								onclick={() => navigateToProject(info.project)}
								onkeydown={(e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); navigateToProject(info.project); } }}
								role="button"
								tabindex="0"
							>
								<div class="project-icon">
									{#if info.project === '(No Project)'}
										📂
									{:else}
										📁
									{/if}
								</div>
								<div class="project-name">{getProjectName(info.project)}</div>
								<button
									class="pin-btn"
									class:pinned={isPinned(info.project)}
									onclick={(e: MouseEvent) => { e.stopPropagation(); togglePin(info.project); }}
									aria-label={isPinned(info.project) ? 'Unpin project' : 'Pin project'}
									title={isPinned(info.project) ? 'Unpin' : 'Pin to top'}
								>
									<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill={isPinned(info.project) ? 'currentColor' : 'none'} stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
										<path d="M12 17v5" />
										<path d="M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16h14v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 2 2 0 0 0 2-2H6a2 2 0 0 0 2 2 1 1 0 0 1 1 1z" />
									</svg>
								</button>
							</div>
							{/each}
						</div>
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
		z-index: 2;
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
		padding: 16px 48px 12px 16px;
		border-bottom: 1px solid var(--color-border, #e5e7eb);
		display: flex;
		flex-direction: column;
		gap: 10px;
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

	.sort-controls {
		display: flex;
		gap: 2px;
		background: rgba(0, 0, 0, 0.05);
		border-radius: 6px;
		padding: 2px;
		align-self: flex-start;
	}

	:global(.dark) .sort-controls {
		background: rgba(255, 255, 255, 0.05);
	}

	.sort-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 26px;
		border: none;
		background: transparent;
		color: rgb(107, 114, 128);
		border-radius: 4px;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	:global(.dark) .sort-btn {
		color: rgb(156, 163, 175);
	}

	.sort-btn:hover {
		color: rgb(17, 24, 39);
	}

	:global(.dark) .sort-btn:hover {
		color: rgb(243, 244, 246);
	}

	.sort-btn.active {
		background: white;
		color: rgb(147, 51, 234);
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
	}

	:global(.dark) .sort-btn.active {
		background: rgb(55, 65, 81);
		color: rgb(168, 85, 247);
	}

	.projects-list {
		flex: 1;
		overflow-y: auto;
		padding: 4px 8px 8px;
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

	.group {
		margin-bottom: 4px;
	}

	.group-heading {
		font-size: 0.6875rem;
		font-weight: 600;
		color: rgb(156, 163, 175);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		padding: 10px 12px 4px;
		position: sticky;
		top: 0;
		background: var(--color-bg-secondary, #f9fafb);
		z-index: 1;
	}

	:global(.dark) .group-heading {
		color: rgb(107, 114, 128);
		background: rgb(31, 41, 55);
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

	.pin-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 24px;
		height: 24px;
		margin-left: auto;
		flex-shrink: 0;
		border: none;
		background: transparent;
		color: rgb(156, 163, 175);
		border-radius: 4px;
		cursor: pointer;
		opacity: 0;
		transition: opacity 0.15s ease, color 0.15s ease;
	}

	.project-item:hover .pin-btn {
		opacity: 1;
	}

	.pin-btn:hover {
		color: rgb(107, 114, 128);
	}

	:global(.dark) .pin-btn:hover {
		color: rgb(209, 213, 219);
	}

	.pin-btn.pinned {
		opacity: 1;
		color: rgb(147, 51, 234);
	}

	:global(.dark) .pin-btn.pinned {
		color: rgb(168, 85, 247);
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
