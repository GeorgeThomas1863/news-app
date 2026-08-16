import { describe, test, expect, beforeEach, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import SourcesModal from "./SourcesModal.jsx";
import {
  addRssSource,
  addTelegramSource,
  deleteSource,
  getSources,
  updateSource,
} from "../api.js";

vi.mock("../api.js", () => ({
  getSources: vi.fn(),
  addRssSource: vi.fn(),
  addTelegramSource: vi.fn(),
  updateSource: vi.fn(),
  deleteSource: vi.fn(),
}));

const sources = {
  rss: [
    { id: "r1", name: "Reuters", url: "https://reuters.com/rss", enabled: true },
    { id: "r2", name: "AP", url: "https://ap.org/rss", enabled: false },
  ],
  telegram: [{ id: "t1", name: "Intel Slava", channel: "intelslava", enabled: true }],
};

async function renderModal(overrides = {}) {
  const props = { onClose: vi.fn(), ...overrides };
  const view = render(<SourcesModal {...props} />);
  await screen.findByText("Reuters");
  return { props, ...view };
}

beforeEach(() => {
  vi.clearAllMocks();
  getSources.mockResolvedValue(sources);
});

describe("SourcesModal", () => {
  test("loads sources on mount and shows the RSS tab by default", async () => {
    await renderModal();

    expect(getSources).toHaveBeenCalledTimes(1);
    expect(screen.getByText("https://reuters.com/rss")).toBeInTheDocument();
    expect(screen.queryByText("intelslava")).not.toBeInTheDocument();
  });

  test("shows the error when the initial load fails", async () => {
    getSources.mockRejectedValue(new Error("Database unavailable"));
    render(<SourcesModal onClose={vi.fn()} />);

    expect(await screen.findByText("Database unavailable")).toBeInTheDocument();
  });

  test("switching tabs shows telegram sources", async () => {
    await renderModal();

    fireEvent.click(screen.getByRole("button", { name: "Telegram Channels" }));

    expect(screen.getByText("intelslava")).toBeInTheDocument();
    expect(screen.queryByText("Reuters")).not.toBeInTheDocument();
  });

  test("adding an RSS source calls the API, clears the form, and reloads", async () => {
    addRssSource.mockResolvedValue({ success: true });
    await renderModal();

    fireEvent.change(screen.getByPlaceholderText("Name"), { target: { value: "BBC" } });
    fireEvent.change(screen.getByPlaceholderText("Feed URL"), {
      target: { value: "https://bbc.com/rss" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));

    await waitFor(() => expect(getSources).toHaveBeenCalledTimes(2));
    expect(addRssSource).toHaveBeenCalledWith("BBC", "https://bbc.com/rss");
    expect(screen.getByPlaceholderText("Name")).toHaveValue("");
    expect(screen.getByPlaceholderText("Feed URL")).toHaveValue("");
  });

  test("submitting an incomplete add form does not call the API", async () => {
    await renderModal();

    fireEvent.change(screen.getByPlaceholderText("Name"), { target: { value: "BBC" } });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));

    expect(addRssSource).not.toHaveBeenCalled();
  });

  test("a failed add shows the error and keeps the form values", async () => {
    addRssSource.mockRejectedValue(new Error("Source already exists"));
    await renderModal();

    fireEvent.change(screen.getByPlaceholderText("Name"), { target: { value: "BBC" } });
    fireEvent.change(screen.getByPlaceholderText("Feed URL"), {
      target: { value: "https://bbc.com/rss" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));

    expect(await screen.findByText("Source already exists")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Name")).toHaveValue("BBC");
    expect(getSources).toHaveBeenCalledTimes(1);
  });

  test("a successful mutation clears a previously shown error", async () => {
    addRssSource.mockRejectedValueOnce(new Error("Source already exists"));
    updateSource.mockResolvedValue({ success: true });
    await renderModal();

    fireEvent.change(screen.getByPlaceholderText("Name"), { target: { value: "BBC" } });
    fireEvent.change(screen.getByPlaceholderText("Feed URL"), {
      target: { value: "https://bbc.com/rss" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));
    await screen.findByText("Source already exists");

    fireEvent.click(screen.getAllByRole("checkbox")[0]);

    await waitFor(() =>
      expect(screen.queryByText("Source already exists")).not.toBeInTheDocument(),
    );
  });

  test("toggling a source flips its enabled flag via the API", async () => {
    updateSource.mockResolvedValue({ success: true });
    await renderModal();

    fireEvent.click(screen.getAllByRole("checkbox")[0]);

    await waitFor(() => expect(updateSource).toHaveBeenCalledWith("r1", { enabled: false }));
  });

  test("editing a source saves the changed fields", async () => {
    updateSource.mockResolvedValue({ success: true });
    await renderModal();

    fireEvent.click(screen.getAllByRole("button", { name: "✎" })[0]);
    fireEvent.change(screen.getByDisplayValue("Reuters"), { target: { value: "Reuters World" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(updateSource).toHaveBeenCalledWith("r1", {
        name: "Reuters World",
        url: "https://reuters.com/rss",
      }),
    );
  });

  test("a successful save exits edit mode", async () => {
    updateSource.mockResolvedValue({ success: true });
    await renderModal();

    fireEvent.click(screen.getAllByRole("button", { name: "✎" })[0]);
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Save" })).not.toBeInTheDocument(),
    );
  });

  test("toggling another source keeps an open edit form and its typed text", async () => {
    updateSource.mockResolvedValue({ success: true });
    await renderModal();

    fireEvent.click(screen.getAllByRole("button", { name: "✎" })[0]);
    fireEvent.change(screen.getByDisplayValue("Reuters"), { target: { value: "Reuters World" } });
    fireEvent.click(screen.getByRole("checkbox"));

    await waitFor(() => expect(getSources).toHaveBeenCalledTimes(2));
    expect(screen.getByDisplayValue("Reuters World")).toBeInTheDocument();
  });

  test("delete only fires after the user confirms", async () => {
    deleteSource.mockResolvedValue({ success: true });
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    await renderModal();

    fireEvent.click(screen.getAllByRole("button", { name: "✕" })[1]);
    expect(deleteSource).not.toHaveBeenCalled();

    confirmSpy.mockReturnValue(true);
    fireEvent.click(screen.getAllByRole("button", { name: "✕" })[1]);
    await waitFor(() => expect(deleteSource).toHaveBeenCalledWith("r1"));

    confirmSpy.mockRestore();
  });

  test("clicking the overlay closes the modal; clicking inside does not", async () => {
    const { props } = await renderModal();

    fireEvent.click(screen.getByText("MANAGE SOURCES"));
    expect(props.onClose).not.toHaveBeenCalled();

    fireEvent.click(document.getElementById("sources-modal-overlay"));
    expect(props.onClose).toHaveBeenCalledTimes(1);
  });
});
