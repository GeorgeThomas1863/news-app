export const AUTH_EXPIRED_EVENT = "auth-expired";

export const apiFetch = async (path, options = {}) => {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (response.status === 401) {
    window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
    throw new Error("Not authenticated");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return response.json();
};

export const login = (password) =>
  apiFetch("/api/auth/login", { method: "POST", body: JSON.stringify({ password }) });

export const logout = () => apiFetch("/api/auth/logout", { method: "POST" });

export const checkAuth = () => apiFetch("/api/auth/check");

export const getStories = () => apiFetch("/api/stories");

export const getTopicStories = (topic, skip, limit) =>
  apiFetch(`/api/stories?topic=${encodeURIComponent(topic)}&skip=${skip}&limit=${limit}`);

export const getStory = (id) => apiFetch(`/api/stories/${id}`);

export const getPipelineStatus = () => apiFetch("/api/pipeline/status");

export const triggerPipelineRun = () => apiFetch("/api/pipeline/run", { method: "POST" });
