/**
 * Operator Authentication Utility
 * Manages admin token stored exclusively in sessionStorage (never hardcoded in repo).
 */

export const getAdminToken = () => {
  try {
    if (typeof window !== 'undefined' && window.sessionStorage) {
      return window.sessionStorage.getItem('admin_token') || '';
    }
  } catch (e) {
    console.warn('Failed to read admin_token from sessionStorage:', e);
  }
  return '';
};

export const setAdminToken = (token) => {
  try {
    if (typeof window !== 'undefined' && window.sessionStorage) {
      if (token) {
        window.sessionStorage.setItem('admin_token', token.trim());
      } else {
        window.sessionStorage.removeItem('admin_token');
      }
    }
  } catch (e) {
    console.warn('Failed to update admin_token in sessionStorage:', e);
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

  let response = await fetch(url, { ...options, headers });

  if (response.status === 401 && typeof window !== 'undefined') {
    const entered = window.prompt(
      'Operator Authentication Required:\nEnter ADMIN_TOKEN (printed in backend startup console):'
    );
    if (entered && entered.trim()) {
      const cleanToken = entered.trim();
      setAdminToken(cleanToken);
      const retryHeaders = {
        ...headers,
        'X-Admin-Token': cleanToken
      };
      response = await fetch(url, { ...options, headers: retryHeaders });
      if (response.status === 401) {
        setAdminToken('');
      }
    } else {
      setAdminToken('');
    }
  }

  return response;
};
