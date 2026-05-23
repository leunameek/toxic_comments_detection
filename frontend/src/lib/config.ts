export const API_BASE = '/api/v1';
export const WS_BASE = '/ws';

export function getSession() {
  if (typeof localStorage === 'undefined') return { userId: '', username: '', apiKey: '' };
  return {
    userId: localStorage.getItem('toxic_user_id') || '',
    username: localStorage.getItem('toxic_username') || '',
    apiKey: localStorage.getItem('toxic_api_key') || 'player-dev-key-1',
  };
}

export function saveSession(userId: string, username: string, apiKey = 'player-dev-key-1') {
  localStorage.setItem('toxic_user_id', userId);
  localStorage.setItem('toxic_username', username);
  localStorage.setItem('toxic_api_key', apiKey);
}

export function generateUserId(): string {
  return 'u_' + Math.random().toString(36).slice(2, 10);
}
