import { useCallback, useEffect, useState } from "react";

import { getSettings, updateSettings } from "../api.js";

const FIELDS = [
  { key: "filter_model", label: "Filter model" },
  { key: "scoring_model", label: "Scoring model" },
];

const SettingsModal = ({ onClose }) => {
  const [settings, setSettings] = useState(null);
  const [selected, setSelected] = useState({ filter_model: "", scoring_model: "" });
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [saving, setSaving] = useState(false);

  // keysToSync: only these keys of `selected` are refreshed from the server;
  // omit it to replace both (initial load). Prevents a reset of one field from
  // wiping an unsaved edit to the other.
  const loadSettings = useCallback(async (keysToSync) => {
    try {
      const body = await getSettings();
      setSettings(body);
      setSelected((prev) => mergeSelected(prev, body, keysToSync));
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  const changeField = (key, value) => {
    setSelected((prev) => ({ ...prev, [key]: value }));
    setMessage(null);
  };

  const runUpdate = async (fields) => {
    setSaving(true);
    try {
      const result = await updateSettings(fields);
      setMessage(result.message || "Saved.");
      setError(null);
      await loadSettings(Object.keys(fields));
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const saveChanges = () => {
    if (!settings) return;
    const fields = {};
    for (const field of FIELDS) {
      if (selected[field.key] !== settings[field.key]) fields[field.key] = selected[field.key];
    }
    if (Object.keys(fields).length === 0) return;
    runUpdate(fields);
  };

  const resetField = (key) => runUpdate({ [key]: null });

  const closeOnOverlayClick = (event) => {
    if (event.target === event.currentTarget) onClose();
  };

  return (
    <div id="settings-modal-overlay" onClick={closeOnOverlayClick}>
      <div id="settings-modal">
        <div id="settings-modal-header">
          <h2>MODEL SETTINGS</h2>
          <button className="settings-close-btn" onClick={onClose}>
            ✕
          </button>
        </div>
        {error && <p className="settings-error">{error}</p>}
        {message && !error && <p className="settings-message">{message}</p>}
        {settings && (
          <div className="settings-body">
            {FIELDS.map((field) => (
              <ModelField
                key={field.key}
                field={field}
                value={selected[field.key]}
                source={settings.sources[field.key]}
                allowedModels={settings.allowed_models}
                onChange={changeField}
                onReset={resetField}
                saving={saving}
              />
            ))}
          </div>
        )}
        <div className="settings-actions">
          <button className="source-add-btn" onClick={saveChanges} disabled={saving || !settings}>
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
};

const mergeSelected = (prev, body, keysToSync) => {
  if (!keysToSync) return { filter_model: body.filter_model, scoring_model: body.scoring_model };
  const next = { ...prev };
  for (const key of keysToSync) next[key] = body[key];
  return next;
};

const ModelField = ({ field, value, source, allowedModels, onChange, onReset, saving }) => {
  const hint = buildSourceHint(source);

  return (
    <div className="settings-field">
      <label className="settings-field-label" htmlFor={`settings-${field.key}`}>
        {field.label}
      </label>
      <select
        id={`settings-${field.key}`}
        className="settings-select"
        value={value}
        onChange={(event) => onChange(field.key, event.target.value)}
      >
        <optgroup label="Anthropic">
          {allowedModels.anthropic.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </optgroup>
        <optgroup label="OpenAI">
          {allowedModels.openai.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </optgroup>
      </select>
      <div className="settings-field-footer">
        {hint && <span className="settings-hint">{hint}</span>}
        <button
          type="button"
          className="settings-reset-btn"
          disabled={saving}
          onClick={() => onReset(field.key)}
        >
          Reset to .env
        </button>
      </div>
    </div>
  );
};

const buildSourceHint = (source) => {
  if (source === "db") return null;
  if (source === "env") return "using .env default";
  return "using built-in default";
};

export default SettingsModal;
