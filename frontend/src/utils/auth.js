/**
 * Operator Authentication Utility
 * Manages admin token stored exclusively in sessionStorage (never hardcoded in repo).
 */

export const getAdminToken = () => {
  if (typeof window === 'undefined') return '';
  let token = sessionStorage.getItem('admin_token');
  if (!token) {
    const entered = window.prompt(
      'Operator Authentication Required:\nEnter ADMIN_TOKEN (printed in backend startup console):'
    );
    if (entered) {
      token = entered.trim();
      sessionStorage.setItem('admin_token', token);
    }
  }
  return token || '';
};

export const setAdminToken = (token) => {
  if (typeof window !== 'undefined') {
    if (token) {
      sessionStorage.setItem('admin_token', token.trim());
    } else {
      sessionStorage.removeItem('admin_token');
    }
  }
};

export const getAuthHeaders = () => {
  const token = getAdminToken();
  return token ? { 'X-Admin-Token': token } : {};
};

export const authFetch = async (url, options = {}) => {
  const headers = {
    ...getAuthHeaders(),
    ...(options.headers || {})
  };

  const response = await fetch(url, { ...options, headers });
  if (response.status === 401) {
    // Clear invalid token from sessionStorage so operator can enter new one
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('admin_token');
    }
    const retry = window.prompt('Invalid ADMIN_TOKEN. Please re-enter operator ADMIN_TOKEN:');
    if (retry) {
      sessionStorage.setItem('admin_token', retry.trim());
      headers['X-Admin-Token'] = retry.trim();
      return fetch(url, { ...options, headers });
    }
  }
  return response;
};
