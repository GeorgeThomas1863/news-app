import { describe, test, expect, afterEach, vi } from "vitest";
import { AUTH_EXPIRED_EVENT, apiFetch } from "./api.js";

function stubFetchResponse({ ok = true, status = 200, body = {} } = {}) {
  const response = {
    ok,
    status,
    json: () => (body instanceof Error ? Promise.reject(body) : Promise.resolve(body)),
  };
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));
  return globalThis.fetch;
}

describe("apiFetch", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("returns parsed JSON and sends JSON content-type", async () => {
    const fetchMock = stubFetchResponse({ body: { stories: [] } });

    const result = await apiFetch("/api/stories");

    expect(result).toEqual({ stories: [] });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/stories",
      expect.objectContaining({ headers: { "Content-Type": "application/json" } }),
    );
  });

  test("passes method and body through to fetch", async () => {
    const fetchMock = stubFetchResponse();

    await apiFetch("/api/auth/login", { method: "POST", body: '{"password":"x"}' });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/login",
      expect.objectContaining({ method: "POST", body: '{"password":"x"}' }),
    );
  });

  test("401 dispatches the auth-expired event and throws", async () => {
    stubFetchResponse({ ok: false, status: 401 });
    const onExpired = vi.fn();
    window.addEventListener(AUTH_EXPIRED_EVENT, onExpired);

    await expect(apiFetch("/api/stories")).rejects.toThrow("Not authenticated");

    expect(onExpired).toHaveBeenCalledTimes(1);
    window.removeEventListener(AUTH_EXPIRED_EVENT, onExpired);
  });

  test("non-401 failure throws the backend's detail message", async () => {
    stubFetchResponse({ ok: false, status: 409, body: { detail: "Source already exists" } });

    await expect(apiFetch("/api/sources/rss")).rejects.toThrow("Source already exists");
  });

  test("failure without a JSON body falls back to the status code", async () => {
    stubFetchResponse({ ok: false, status: 503, body: new Error("not json") });

    await expect(apiFetch("/api/stories")).rejects.toThrow("Request failed (503)");
  });

  test("failure with JSON but no detail field falls back to the status code", async () => {
    stubFetchResponse({ ok: false, status: 500, body: {} });

    await expect(apiFetch("/api/stories")).rejects.toThrow("Request failed (500)");
  });
});
