/**
 * Theme store for dark/light mode
 */

import { writable } from 'svelte/store';
import { browser } from '$app/environment';

type Theme = 'light' | 'dark';

function createThemeStore() {
	// Initialize from localStorage or system preference
	const initialTheme: Theme = browser
		? (localStorage.getItem('theme') as Theme) ||
		  (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
		: 'light';

	const { subscribe, set, update } = writable<Theme>(initialTheme);

	// Apply theme to document
	if (browser) {
		applyTheme(initialTheme);
	}

	return {
		subscribe,
		toggle: () =>
			update((current) => {
				const newTheme = current === 'light' ? 'dark' : 'light';
				if (browser) {
					localStorage.setItem('theme', newTheme);
					applyTheme(newTheme);
				}
				return newTheme;
			}),
		set: (theme: Theme) => {
			if (browser) {
				localStorage.setItem('theme', theme);
				applyTheme(theme);
			}
			set(theme);
		}
	};
}

function applyTheme(theme: Theme) {
	if (theme === 'dark') {
		document.documentElement.classList.add('dark');
	} else {
		document.documentElement.classList.remove('dark');
	}
}

export const theme = createThemeStore();
