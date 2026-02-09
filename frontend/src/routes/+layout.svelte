<script lang="ts">
	import { onMount } from 'svelte';
	import '../app.css';
	import ThemeToggle from '$lib/components/ThemeToggle.svelte';
	import RefreshButton from '$lib/components/RefreshButton.svelte';
	import ProjectsSidebar from '$lib/components/ProjectsSidebar.svelte';
	import { theme } from '$lib/stores/theme';

	let mobileMenuOpen = false;
	let isMobile = false;

	onMount(() => {
		const checkMobile = () => {
			isMobile = window.innerWidth <= 768;
			if (!isMobile) mobileMenuOpen = false;
		};

		checkMobile();
		window.addEventListener('resize', checkMobile);

		return () => {
			window.removeEventListener('resize', checkMobile);
		};
	});

	function toggleMenu() {
		mobileMenuOpen = !mobileMenuOpen;
	}

	function closeMenu() {
		mobileMenuOpen = false;
	}
</script>

<div class="app" class:mobile-menu-open={mobileMenuOpen}>
	{#if isMobile}
		<!-- Mobile overlay -->
		{#if mobileMenuOpen}
			<button class="overlay" on:click={closeMenu} aria-label="Close menu"></button>
		{/if}

		<!-- Mobile sidebar -->
		<aside class="mobile-sidebar" class:open={mobileMenuOpen}>
			<ProjectsSidebar onNavigate={closeMenu} />
		</aside>
	{:else}
		<!-- Desktop sidebar -->
		<ProjectsSidebar />
	{/if}

	<div class="main-area">
		<header>
			{#if isMobile}
				<button class="menu-btn" on:click={toggleMenu} aria-label="Toggle menu">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						width="24"
						height="24"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						{#if mobileMenuOpen}
							<line x1="18" y1="6" x2="6" y2="18"></line>
							<line x1="6" y1="6" x2="18" y2="18"></line>
						{:else}
							<line x1="3" y1="12" x2="21" y2="12"></line>
							<line x1="3" y1="6" x2="21" y2="6"></line>
							<line x1="3" y1="18" x2="21" y2="18"></line>
						{/if}
					</svg>
				</button>
			{/if}

			<a href="/" class="logo">
				<span class="logo-icon">📚</span>
				<span class="logo-text">Session Viewer</span>
			</a>

			<div class="header-controls">
				<RefreshButton />
				<ThemeToggle />
			</div>
		</header>

		<main>
			<slot />
		</main>
	</div>
</div>

<style>
	.app {
		display: flex;
		height: 100vh;
		overflow: hidden;
	}

	.main-area {
		flex: 1;
		display: flex;
		flex-direction: column;
		min-width: 0;
	}

	header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 16px 24px;
		border-bottom: 1px solid var(--color-border, #e5e7eb);
		background: var(--color-bg-primary, white);
		gap: 16px;
	}

	:global(.dark) header {
		background: rgb(17, 24, 39);
		border-bottom-color: rgb(55, 65, 81);
	}

	.menu-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 40px;
		height: 40px;
		background: transparent;
		border: none;
		color: rgb(17, 24, 39);
		border-radius: 8px;
		transition: background-color 0.15s ease;
		cursor: pointer;
	}

	:global(.dark) .menu-btn {
		color: rgb(243, 244, 246);
	}

	.menu-btn:hover {
		background: rgba(0, 0, 0, 0.05);
	}

	:global(.dark) .menu-btn:hover {
		background: rgba(255, 255, 255, 0.05);
	}

	.logo {
		display: flex;
		align-items: center;
		gap: 10px;
		font-size: 1.25rem;
		font-weight: 600;
		color: rgb(17, 24, 39);
		text-decoration: none;
		transition: color 0.15s ease;
	}

	:global(.dark) .logo {
		color: rgb(243, 244, 246);
	}

	.logo:hover {
		text-decoration: none;
		color: rgb(147, 51, 234);
	}

	:global(.dark) .logo:hover {
		color: rgb(168, 85, 247);
	}

	.logo-icon {
		font-size: 1.5rem;
	}

	.header-controls {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-left: auto;
	}

	main {
		flex: 1;
		overflow-y: auto;
		overflow-x: hidden;
	}

	/* Mobile styles */
	.overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		backdrop-filter: blur(4px);
		z-index: 40;
		border: none;
		cursor: pointer;
	}

	.mobile-sidebar {
		position: fixed;
		top: 0;
		left: 0;
		bottom: 0;
		width: 85%;
		max-width: 360px;
		z-index: 50;
		transform: translateX(-100%);
		transition: transform 0.2s ease;
		background: var(--color-bg-secondary, #f9fafb);
		box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
	}

	:global(.dark) .mobile-sidebar {
		background: rgb(31, 41, 55);
	}

	.mobile-sidebar.open {
		transform: translateX(0);
	}

	@media (max-width: 768px) {
		header {
			padding: 12px 16px;
		}

		.logo-text {
			display: none;
		}

		.header-controls {
			gap: 4px;
		}
	}
</style>
