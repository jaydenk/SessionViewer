/**
 * Utility functions
 */
import { marked } from 'marked';

marked.use({ async: false, breaks: true, gfm: true });

/**
 * Render markdown content to HTML
 */
export function renderMarkdown(content: string): string {
	try {
		return marked.parse(content) as string;
	} catch {
		return content;
	}
}

/**
 * Format a date string for display
 */
export function formatDate(dateStr: string): string {
	const date = new Date(dateStr.endsWith('Z') ? dateStr : dateStr + 'Z');
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
			year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
		});
	}
}

/**
 * Format relative time
 */
export function formatRelativeTime(dateStr: string): string {
	const date = new Date(dateStr.endsWith('Z') ? dateStr : dateStr + 'Z');
	const now = new Date();
	const diffMs = now.getTime() - date.getTime();
	const diffSeconds = Math.floor(diffMs / 1000);
	const diffMinutes = Math.floor(diffSeconds / 60);
	const diffHours = Math.floor(diffMinutes / 60);
	const diffDays = Math.floor(diffHours / 24);

	if (diffSeconds < 60) {
		return 'just now';
	} else if (diffMinutes < 60) {
		return `${diffMinutes}m ago`;
	} else if (diffHours < 24) {
		return `${diffHours}h ago`;
	} else if (diffDays < 30) {
		return `${diffDays}d ago`;
	} else {
		return date.toLocaleDateString();
	}
}

/**
 * Truncate text to a maximum length
 */
export function truncate(text: string, maxLength: number): string {
	if (text.length <= maxLength) return text;
	return text.substring(0, maxLength) + '...';
}

/**
 * Debounce function
 */
export function debounce<T extends (...args: any[]) => any>(
	func: T,
	wait: number
): (...args: Parameters<T>) => void {
	let timeout: ReturnType<typeof setTimeout> | null = null;

	return function executedFunction(...args: Parameters<T>) {
		const later = () => {
			timeout = null;
			func(...args);
		};

		if (timeout) clearTimeout(timeout);
		timeout = setTimeout(later, wait);
	};
}
