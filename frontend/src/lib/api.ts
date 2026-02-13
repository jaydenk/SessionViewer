/**
 * API client for Session Viewer backend
 */

import type {
	Session,
	SessionsResponse,
	Message,
	Subagent,
	AssociatedFile,
	SessionFilters,
	IndexStatus,
	ProjectInfo
} from './types';

const API_BASE = import.meta.env.DEV ? 'http://localhost:8000/api' : '/api';

/**
 * Fetch wrapper with error handling
 */
async function fetchAPI<T>(url: string, options?: RequestInit): Promise<T> {
	try {
		const response = await fetch(`${API_BASE}${url}`, {
			...options,
			headers: {
				'Content-Type': 'application/json',
				...options?.headers
			}
		});

		if (!response.ok) {
			const error = await response.text();
			throw new Error(`API error: ${response.status} ${error}`);
		}

		return await response.json();
	} catch (error) {
		console.error('API fetch error:', error);
		throw error;
	}
}

/**
 * Build query string from filters
 */
function buildQueryString(filters: Partial<SessionFilters>): string {
	const params = new URLSearchParams();

	Object.entries(filters).forEach(([key, value]) => {
		if (value !== null && value !== undefined && value !== '') {
			params.append(key, String(value));
		}
	});

	return params.toString();
}

/**
 * Get list of sessions with filters
 */
export async function getSessions(filters: Partial<SessionFilters> = {}): Promise<SessionsResponse> {
	const query = buildQueryString(filters);
	return fetchAPI<SessionsResponse>(`/sessions?${query}`);
}

/**
 * Get detailed session information
 */
export async function getSession(sessionId: string): Promise<Session> {
	return fetchAPI<Session>(`/sessions/${sessionId}`);
}

/**
 * Get messages for a session
 */
export async function getSessionMessages(sessionId: string): Promise<Message[]> {
	return fetchAPI<Message[]>(`/sessions/${sessionId}/messages`);
}

/**
 * Get subagents for a session
 */
export async function getSessionSubagents(sessionId: string): Promise<Subagent[]> {
	return fetchAPI<Subagent[]>(`/sessions/${sessionId}/subagents`);
}

/**
 * Get messages for a specific subagent
 */
export async function getSubagentMessages(
	sessionId: string,
	agentId: string
): Promise<Message[]> {
	return fetchAPI<Message[]>(`/sessions/${sessionId}/subagents/${agentId}/messages`);
}

/**
 * Get associated files for a session
 */
export async function getSessionFiles(sessionId: string): Promise<AssociatedFile[]> {
	return fetchAPI<AssociatedFile[]>(`/sessions/${sessionId}/files`);
}

/**
 * Get list of unique projects
 */
export async function getProjects(): Promise<ProjectInfo[]> {
	return fetchAPI<ProjectInfo[]>('/sessions/projects/list');
}

/**
 * Get markdown files from a project directory
 */
export async function getProjectFiles(projectPath: string): Promise<AssociatedFile[]> {
	return fetchAPI<AssociatedFile[]>(`/sessions/projects/${encodeURIComponent(projectPath)}/files`);
}

/**
 * Get indexing status
 */
export async function getIndexStatus(): Promise<IndexStatus> {
	return fetchAPI<IndexStatus>('/index/status');
}

/**
 * Trigger re-indexing
 */
export async function refreshIndex(force: boolean = false): Promise<{ status: string }> {
	return fetchAPI<{ status: string }>(`/index/refresh?force=${force}`, {
		method: 'POST'
	});
}

/**
 * Export sessions as a combined PDF
 */
export async function exportSessionsPdf(sessionIds: string[]): Promise<Blob> {
	const response = await fetch(`${API_BASE}/sessions/export/pdf`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ session_ids: sessionIds })
	});

	if (!response.ok) {
		const error = await response.text();
		throw new Error(`Export failed: ${response.status} ${error}`);
	}

	return response.blob();
}
