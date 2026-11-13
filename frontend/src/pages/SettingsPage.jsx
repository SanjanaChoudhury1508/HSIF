
import { useState } from "react";
import AppShell from "../components/AppShell";

const initialSettings = {
  language: "English",
  showHumanState: true,
  showStrategy: true,
  detectPauses: true,
  saveHistory: true,
  saveRecordings: false,
};

function loadSettings() {
  try {
    const saved = JSON.parse(localStorage.getItem("hsif-settings") || "null");

    return saved && typeof saved === "object"
      ? { ...initialSettings, ...saved }
      : { ...initialSettings };
  } catch {
    return { ...initialSettings };
  }
}

function Toggle({ label, checked, onChange, description }) {
  return (
    <label className="setting-row">
      <span>
        <strong>{label}</strong>
        {description && <small>{description}</small>}
      </span>
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
      />
    </label>
  );
}

export default function SettingsPage() {
  const [settings, setSettings] = useState(loadSettings);
  const [savedMessage, setSavedMessage] = useState("");

  function updateSetting(key, value) {
    setSettings((current) => ({ ...current, [key]: value }));
    setSavedMessage("");
  }

  function saveSettings(event) {
    event.preventDefault();

    try {
      localStorage.setItem("hsif-settings", JSON.stringify(settings));
      window.dispatchEvent(new Event("hsif-settings-updated"));
      setSavedMessage("Preferences saved on this device.");
    } catch {
      setSavedMessage("Could not save preferences. Check browser storage.");
    }
  }

  function resetSettings() {
    const defaults = { ...initialSettings };
    setSettings(defaults);
    try {
      localStorage.setItem("hsif-settings", JSON.stringify(defaults));
      window.dispatchEvent(new Event("hsif-settings-updated"));
      setSavedMessage("Preferences reset to defaults.");
    } catch {
      setSavedMessage("Could not reset preferences.");
    }
  }

  return (
    <AppShell
      title="Settings"
      subtitle="Choose how HSIF listens and what it keeps"
    >
      <form className="narrow" onSubmit={saveSettings}>
        <section className="panel">
          <h2>Audio</h2>

          <div className="field">
            <label htmlFor="microphone">Microphone</label>
            <select id="microphone" defaultValue="default">
              <option value="default">System default microphone</option>
            </select>
            <p className="hint">
              Microphone selection is currently managed by your browser.
            </p>
          </div>

          <div className="field">
            <label htmlFor="language">Speech language</label>
            <select
              id="language"
              value={settings.language}
              onChange={(event) =>
                updateSetting("language", event.target.value)
              }
            >
              <option>English</option>
              <option>Hindi</option>
              <option>Telugu</option>
            </select>
            <p className="hint">
              Saved as a preference. Backend transcription language is not
              connected to this setting yet.
            </p>
          </div>
        </section>

        <section className="panel">
          <h2>Analysis</h2>

          <Toggle
            label="Show human state panel"
            description="Display confidence, engagement and other state indicators."
            checked={settings.showHumanState}
            onChange={(value) => updateSetting("showHumanState", value)}
          />

          <Toggle
            label="Show recommended strategy"
            description="Display the dialogue strategy selected by HSIF."
            checked={settings.showStrategy}
            onChange={(value) => updateSetting("showStrategy", value)}
          />

          <Toggle
            label="Detect pauses automatically"
            description="Preference saved locally; backend behavior is unchanged."
            checked={settings.detectPauses}
            onChange={(value) => updateSetting("detectPauses", value)}
          />
        </section>

        <section className="panel">
          <h2>Privacy</h2>

          <Toggle
            label="Save session history"
            description="Preference only. Session persistence is currently controlled by the backend."
            checked={settings.saveHistory}
            onChange={(value) => updateSetting("saveHistory", value)}
          />

          <Toggle
            label="Save recordings"
            description="Preference only. Audio recording storage is not implemented."
            checked={settings.saveRecordings}
            onChange={(value) => updateSetting("saveRecordings", value)}
          />
        </section>

        <div className="btn-row">
          <button className="btn btn-primary" type="submit">
            Save settings
          </button>

          <button
            className="btn btn-ghost"
            type="button"
            onClick={resetSettings}
          >
            Reset defaults
          </button>
        </div>

        {savedMessage && (
          <p className="save-note" role="status">
            {savedMessage}
          </p>
        )}
      </form>
    </AppShell>
  );
}