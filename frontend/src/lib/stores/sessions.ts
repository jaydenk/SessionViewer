/**
 * Sessions store
 */

import { writable } from 'svelte/store';
import type { SessionsResponse } from '../types';
import { getSessions } from '../api';
import { filters } from './filters';

interface SessionsState {
	data: SessionsResponse | null;
	loading: boolean;
	error: string | null;
}

const initialState: SessionsState = {
	data: null,
	loading: false,
	error: null
};

function createSessionsStore() {
	const { subscribe, set, update } = writable<SessionsState>(initialState);

	return {
		subscribe,
		load: async (filterParams: any = {}) => {
			update((state) => ({ ...state, loading: true, error: null }));

			try {
				const data = await getSessions(filterParams);
				set({ data, loading: false, error: null });
			} catch (error) {
				const message = error instanceof Error ? error.message : 'Failed to load sessions';
				set({ data: null, loading: false, error: message });
			}
		},
		reset: () => set(initialState)
	};
}

export const sessions = createSessionsStore();
