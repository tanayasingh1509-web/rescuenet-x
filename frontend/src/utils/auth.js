/**
 * Operator Authentication Utility
 * Admin token lives only in sessionStorage (never hardcoded in the repo).
 *
 * Behaviour:
 *  - Requests are sent WITHOUT prompting first. In DEMO_MODE the backend lets
 *    dispatch / resolve / reset through, so visitors never see a token prompt.
 *  - Only when the server answers 401 do we ask the operator for the token,
 *    once, then retry. Cancelling returns the 401 so callers can show a message.
 */

const TOKEN_KEY = 'admin_token';

export const getStoredAdminToken = () => {
  if (typeof window === 'undefined') return '';
  try {
    return sessionStorage.getItem(TOKEN_KEY) || '';
  } catch {
    return '';
  }
};

export const getAdminToken = getStoredAdminToken;

export const setAdminToken = (token) => {
  if (typeof window === 'undefined') return;
  try {
    if (token) {
      sessionStorage.setItem(TOKEN_KEY, token.trim());
    } else {
      sessionStorage.removeItem(TOKEN_KEY);
    }
  } catch {
    // sessionStorage can be unavailable (private mode / blocked storage)
  }
};

export const getAuthHeaders = () => {
  const token = getStoredAdminToken();
  return token ? { 'X-Admin-Token': token } : {};
};

const promptForToken = (message) => {
  if (typeof window === 'undefined') return '';
  const entered = window.prompt(message);
  return entered ? entered.trim() : '';
};

export const authFetch = async (url, options = {}) => {
  const baseHeaders = options.headers || {};

  // 1st attempt: silently use a stored token if we have one, otherwise none.
  let response = await fetch(url, {
    ...options,
    headers: { ...getAuthHeaders(), ...baseHeaders }
  });

  if (response.status !== 401) return response;

  // Server wants a token. Drop any stale one and ask exactly once.
  const hadToken = Boolean(getStoredAdminToken());
  setAdminToken('');
  const token = promptForToken(
    hadToken
      ? 'Saved operator token was rejected.\nEnter a valid ADMIN_TOKEN (Render dashboard > Environment):'
      : 'Operator token required for this action.\nEnter ADMIN_TOKEN (Render dashboard > Environment):'
  );
  if (!token) return response; // cancelled: caller sees the 401

  setAdminToken(token);
  response = await fetch(url, {
    ...options,
    headers: { 'X-Admin-Token': token, ...baseHeaders }
  });
  if (response.status === 401) setAdminToken('');

  return response;
};
