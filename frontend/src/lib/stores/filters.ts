/**
 * Session filters store
 */

import { writable } from 'svelte/store';
import type { SessionFilters } from '../types';

const defaultFilters: SessionFilters = {
	source: null,
	project: null,
	search: null,
	date_from: null,
	date_to: null,
	page: 1,
	page_size: 50
};

function createFiltersStore() {
	const { subscribe, set, update } = writable<SessionFilters>(defaultFilters);

	return {
		subscribe,
		set,
		update,
		reset: () => set(defaultFilters),
		setSource: (source: string | null) => update((f) => ({ ...f, source, page: 1 })),
		setProject: (project: string | null) => update((f) => ({ ...f, project, page: 1 })),
		setSearch: (search: string | null) => update((f) => ({ ...f, search, page: 1 })),
		setDateRange: (date_from: string | null, date_to: string | null) =>
			update((f) => ({ ...f, date_from, date_to, page: 1 })),
		setPage: (page: number) => update((f) => ({ ...f, page }))
	};
}

export const filters = createFiltersStore();
