import { useState, useEffect } from 'react';
import './Settings.css';

const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'es', label: 'Spanish' },
  { code: 'fr', label: 'French' },
  { code: 'de', label: 'German' },
  { code: 'zh', label: 'Chinese' },
];

function Settings() {
  const [language, setLanguage] = useState('en');
  const [questionsPerDay, setQuestionsPerDay] = useState(10);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const response = await fetch(`${import.meta.env.VITE_API_URL}/settings/`);
        if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
        const result = await response.json();
        setLanguage(result.language);
        setQuestionsPerDay(result.questions_per_day);
      } catch (err) {
        setError(err.message);
      }
    };
    fetchSettings();
  }, []);

  const saveSettings = async () => {
    setStatus(null);
    setError(null);
    const count = parseInt(questionsPerDay, 10);
    if (isNaN(count) || count < 1) {
      setError('Number of questions must be at least 1.');
      return;
    }
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/settings/`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language, questions_per_day: count }),
      });
      if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
      const result = await response.json();
      setLanguage(result.language);
      setQuestionsPerDay(result.questions_per_day);
      setStatus('Settings saved.');
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="settings-card">
      <h2 className="settings-title">Settings</h2>

      <label className="settings-field">
        <span className="settings-label">Language</span>
        <select
          className="settings-select"
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
        >
          {LANGUAGES.map((lang) => (
            <option key={lang.code} value={lang.code}>{lang.label}</option>
          ))}
        </select>
      </label>

      <label className="settings-field">
        <span className="settings-label">Questions per practice</span>
        <input
          className="settings-input"
          type="number"
          min="1"
          value={questionsPerDay}
          onChange={(e) => setQuestionsPerDay(e.target.value)}
        />
      </label>

      <button className="settings-save" onClick={saveSettings}>Save</button>

      {status && <p className="settings-status">{status}</p>}
      {error && <p className="settings-error">Error: {error}</p>}
    </div>
  );
}

export default Settings;
