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

export const stopPipeline = () => apiFetch("/api/pipeline/stop", { method: "POST" });

export const resumePipeline = () => apiFetch("/api/pipeline/resume", { method: "POST" });

export const getSources = () => apiFetch(`/api/sources`);

export const addRssSource = (name, url) =>
  apiFetch(`/api/sources/rss`, { method: "POST", body: JSON.stringify({ name, url }) });

export const addTelegramSource = (channel) =>
  apiFetch(`/api/sources/telegram`, { method: "POST", body: JSON.stringify({ channel }) });

export const updateSource = (id, fields) =>
  apiFetch(`/api/sources/${id}`, { method: "PUT", body: JSON.stringify(fields) });

export const deleteSource = (id) =>
  apiFetch(`/api/sources/${id}`, { method: "DELETE" });
