import { describe, test, expect, beforeEach, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import SettingsModal from "./SettingsModal.jsx";
import { getSettings, updateSettings } from "../api.js";

vi.mock("../api.js", () => ({
  getSettings: vi.fn(),
  updateSettings: vi.fn(),
}));

const settings = {
  filter_model: "claude-haiku-4-5",
  scoring_model: "claude-sonnet-4-5",
  sources: { filter_model: "db", scoring_model: "env" },
  allowed_models: {
    anthropic: [
      { value: "claude-haiku-4-5", label: "Claude Haiku 4.5" },
      { value: "claude-sonnet-4-5", label: "Claude Sonnet 4.5" },
    ],
    openai: [{ value: "gpt-5.6", label: "GPT-5.6" }],
  },
};

async function renderModal(overrides = {}) {
  const props = { onClose: vi.fn(), ...overrides };
  const view = render(<SettingsModal {...props} />);
  await screen.findByText("MODEL SETTINGS");
  await screen.findByLabelText("Filter model");
  return { props, ...view };
}

beforeEach(() => {
  vi.clearAllMocks();
  getSettings.mockResolvedValue(settings);
});

describe("SettingsModal", () => {
  test("renders options grouped by provider from the loaded settings", async () => {
    await renderModal();

    expect(getSettings).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText("Filter model")).toHaveValue("claude-haiku-4-5");
    expect(screen.getByLabelText("Scoring model")).toHaveValue("claude-sonnet-4-5");
    expect(screen.getAllByText("GPT-5.6")).toHaveLength(2);
  });

  test("shows a hint only for fields not sourced from the db", async () => {
    await renderModal();

    const hints = screen.getAllByText(/using .env default|using built-in default/);
    expect(hints).toHaveLength(1);
    expect(hints[0]).toHaveTextContent("using .env default");
  });

  test("shows the error when the initial load fails", async () => {
    getSettings.mockRejectedValue(new Error("Database unavailable"));
    render(<SettingsModal onClose={vi.fn()} />);

    expect(await screen.findByText("Database unavailable")).toBeInTheDocument();
  });

  test("save sends only the changed fields", async () => {
    updateSettings.mockResolvedValue({ success: true, message: "Saved." });
    await renderModal();

    fireEvent.change(screen.getByLabelText("Scoring model"), {
      target: { value: "gpt-5.6" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(updateSettings).toHaveBeenCalledWith({ scoring_model: "gpt-5.6" }),
    );
    expect(await screen.findByText("Saved.")).toBeInTheDocument();
  });

  test("reset sends null for that field", async () => {
    updateSettings.mockResolvedValue({ success: true, message: "Reset." });
    await renderModal();

    fireEvent.click(screen.getAllByRole("button", { name: "Reset to .env" })[1]);

    await waitFor(() =>
      expect(updateSettings).toHaveBeenCalledWith({ scoring_model: null }),
    );
  });

  test("resetting one field keeps an unsaved edit to the other field", async () => {
    updateSettings.mockResolvedValue({ success: true, message: "Reset." });
    await renderModal();

    fireEvent.change(screen.getByLabelText("Filter model"), {
      target: { value: "claude-sonnet-4-5" },
    });
    fireEvent.click(screen.getAllByRole("button", { name: "Reset to .env" })[1]);

    await waitFor(() =>
      expect(updateSettings).toHaveBeenCalledWith({ scoring_model: null }),
    );
    await screen.findByText("Reset.");
    expect(screen.getByLabelText("Filter model")).toHaveValue("claude-sonnet-4-5");
  });

  test("a failed save shows the error", async () => {
    updateSettings.mockRejectedValue(new Error("Invalid model"));
    await renderModal();

    fireEvent.change(screen.getByLabelText("Filter model"), {
      target: { value: "claude-sonnet-4-5" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("Invalid model")).toBeInTheDocument();
  });
});
