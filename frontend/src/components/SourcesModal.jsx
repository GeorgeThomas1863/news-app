import { useCallback, useEffect, useState } from "react";

import {
  addRssSource,
  addTelegramSource,
  deleteSource,
  getSources,
  updateSource,
} from "../api.js";

const SourcesModal = ({ onClose }) => {
  const [sources, setSources] = useState({ rss: [], telegram: [] });
  const [activeTab, setActiveTab] = useState("rss");
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState(null);

  const loadSources = useCallback(async () => {
    try {
      const body = await getSources();
      setSources(body);
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    loadSources();
  }, [loadSources]);

  // Shared by every mutating action so success/failure handling — clearing or
  // showing the one error slot, exiting edit mode, reloading the list — stays
  // in one place.
  const runMutation = async (action) => {
    try {
      await action();
      setError(null);
      setEditingId(null);
      await loadSources();
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    }
  };

  const switchTab = (tab) => {
    setActiveTab(tab);
    setEditingId(null);
  };

  const toggleEnabled = (source) =>
    runMutation(() => updateSource(source.id, { enabled: !source.enabled }));

  const saveEdit = (id, fields) => runMutation(() => updateSource(id, fields));

  const addRss = (name, url) => runMutation(() => addRssSource(name, url));

  const addTelegram = (channel) => runMutation(() => addTelegramSource(channel));

  const removeSource = (source) => {
    if (!window.confirm(`Delete "${source.name}"?`)) return;
    runMutation(() => deleteSource(source.id));
  };

  const closeOnOverlayClick = (event) => {
    if (event.target === event.currentTarget) onClose();
  };

  const activeSources = sources[activeTab];

  return (
    <div id="sources-modal-overlay" onClick={closeOnOverlayClick}>
      <div id="sources-modal">
        <div id="sources-modal-header">
          <h2>MANAGE SOURCES</h2>
          <button className="sources-close-btn" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="sources-tabs">
          <button
            className={`sources-tab ${activeTab === "rss" ? "active" : ""}`}
            onClick={() => switchTab("rss")}
          >
            RSS Feeds
          </button>
          <button
            className={`sources-tab ${activeTab === "telegram" ? "active" : ""}`}
            onClick={() => switchTab("telegram")}
          >
            Telegram Channels
          </button>
        </div>
        {error && <p className="sources-error">{error}</p>}
        <div className="sources-list">
          {activeSources.map((source) => (
            <SourceRow
              key={source.id}
              source={source}
              type={activeTab}
              editing={editingId === source.id}
              onToggle={toggleEnabled}
              onStartEdit={setEditingId}
              onCancelEdit={() => setEditingId(null)}
              onSave={saveEdit}
              onDelete={removeSource}
            />
          ))}
        </div>
        <SourceAddForm type={activeTab} onAddRss={addRss} onAddTelegram={addTelegram} />
      </div>
    </div>
  );
};

const SourceRow = ({
  source,
  type,
  editing,
  onToggle,
  onStartEdit,
  onCancelEdit,
  onSave,
  onDelete,
}) => {
  if (editing) {
    return <SourceEditForm source={source} type={type} onSave={onSave} onCancel={onCancelEdit} />;
  }

  const detail = type === "rss" ? source.url : source.channel;

  return (
    <div className="source-row">
      <span className="source-row-name">{source.name}</span>
      <span className="source-row-detail">{detail}</span>
      <div className="source-row-actions">
        <input
          type="checkbox"
          className="source-toggle"
          checked={source.enabled}
          onChange={() => onToggle(source)}
        />
        <button className="source-edit-btn" onClick={() => onStartEdit(source.id)}>
          ✎
        </button>
        <button className="source-delete-btn" onClick={() => onDelete(source)}>
          ✕
        </button>
      </div>
    </div>
  );
};

const SourceEditForm = ({ source, type, onSave, onCancel }) => {
  const [name, setName] = useState(source.name);
  const [url, setUrl] = useState(source.url || "");
  const [channel, setChannel] = useState(source.channel || "");
  const [submitting, setSubmitting] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    if (submitting) return;

    setSubmitting(true);
    const fields = type === "rss" ? { name, url } : { channel };
    await onSave(source.id, fields);
    setSubmitting(false);
  };

  return (
    <form className="source-edit-form" onSubmit={submit}>
      {type === "rss" ? (
        <>
          <input
            className="source-input"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
          <input
            className="source-input"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
          />
        </>
      ) : (
        <input
          className="source-input"
          value={channel}
          onChange={(event) => setChannel(event.target.value)}
        />
      )}
      <button type="submit" disabled={submitting}>
        {submitting ? "Saving…" : "Save"}
      </button>
      <button type="button" onClick={onCancel}>
        Cancel
      </button>
    </form>
  );
};

const SourceAddForm = ({ type, onAddRss, onAddTelegram }) => {
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [channel, setChannel] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    if (submitting) return;
    if (type === "rss" && (!name || !url)) return;
    if (type === "telegram" && !channel) return;

    setSubmitting(true);
    const success = type === "rss" ? await onAddRss(name, url) : await onAddTelegram(channel);
    if (success) {
      setName("");
      setUrl("");
      setChannel("");
    }
    setSubmitting(false);
  };

  return (
    <form className="source-add-form" onSubmit={submit}>
      {type === "rss" ? (
        <>
          <input
            className="source-input"
            placeholder="Name"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
          <input
            className="source-input"
            placeholder="Feed URL"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
          />
        </>
      ) : (
        <input
          className="source-input"
          placeholder="Channel"
          value={channel}
          onChange={(event) => setChannel(event.target.value)}
        />
      )}
      <button className="source-add-btn" type="submit" disabled={submitting}>
        {submitting ? "Adding…" : "Add"}
      </button>
    </form>
  );
};

export default SourcesModal;
