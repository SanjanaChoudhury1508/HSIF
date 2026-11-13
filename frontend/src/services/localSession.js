export const USER_STORAGE_KEY = "hsif-user";
export const ACTIVE_SESSION_STORAGE_KEY = "hsif.activeSessionId";

export function clearLocalUserSession(storage = localStorage) {
  storage.removeItem(USER_STORAGE_KEY);
  storage.removeItem(ACTIVE_SESSION_STORAGE_KEY);
}

export function getRestorableSessionId(storage = localStorage) {
  if (!storage.getItem(USER_STORAGE_KEY)) return null;
  return storage.getItem(ACTIVE_SESSION_STORAGE_KEY) || null;
}
