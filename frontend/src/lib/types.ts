/**
 * TypeScript type definitions for Session Viewer
 */

export interface Session {
	id: string;
	source: 'claude' | 'codex';
	project: string | null;
	cwd: string | null;
	model: string | null;
	display: string | null;
	created_at: string;
	updated_at: string;
	message_count: number;
	subagent_count: number;
	has_tool_results: boolean;
	file_path?: string;
	indexed_at?: string;
}

export interface SessionsResponse {
	sessions: Session[];
	total: number;
	page: number;
	page_size: number;
	total_pages: number;
}

export interface Message {
	id: string;
	session_id: string;
	parent_uuid: string | null;
	type: 'user' | 'assistant';
	content: string;
	content_preview: string | null;
	timestamp: string;
	sequence: number;
	agent_id: string | null;
	model: string | null;
	usage_input_tokens: number | null;
	usage_output_tokens: number | null;
}

export interface Subagent {
	id: string;
	session_id: string;
	agent_id: string;
	message_count: number;
	first_message: string | null;
	file_path: string | null;
}

export interface ToolResult {
	id: string;
	session_id: string;
	tool_use_id: string;
	content: string | null;
	content_preview: string | null;
	file_path: string | null;
}

export interface AssociatedFile {
	id: string;
	session_id: string;
	file_type: 'todo' | 'plan' | 'debug';
	content: string | null;
	file_path: string;
}

export interface ProjectInfo {
	project: string;
	last_activity: string;
}

export interface SessionFilters {
	source: string | null;
	project: string | null;
	search: string | null;
	date_from: string | null;
	date_to: string | null;
	page: number;
	page_size: number;
}

export interface IndexStatus {
	is_indexing: boolean;
	last_indexed: string | null;
	total_sessions: number;
	claude_sessions: number;
	codex_sessions: number;
}
