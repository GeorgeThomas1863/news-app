import { useState } from "react";

import { login } from "../api.js";

const Login = ({ onLogin }) => {
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const submitPassword = async (event) => {
    event.preventDefault();
    if (!password || submitting) return;

    setSubmitting(true);
    setError(null);
    try {
      await login(password);
      onLogin();
    } catch {
      setError("Wrong password");
      setSubmitting(false);
    }
  };

  return (
    <div id="auth-page">
      <form id="auth-form-wrapper" onSubmit={submitPassword}>
        <h1 id="auth-title">NEWS</h1>
        <label id="auth-label" htmlFor="auth-pw">
          Password
        </label>
        <div className="password-input-wrapper">
          <input
            id="auth-pw"
            className="password-input"
            type={showPassword ? "text" : "password"}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Enter password"
            autoFocus
          />
          <button
            type="button"
            className="password-toggle-btn"
            onClick={() => setShowPassword(!showPassword)}
          >
            {showPassword ? "hide" : "show"}
          </button>
        </div>
        {error && <p className="auth-error">{error}</p>}
        <button className="btn-submit" type="submit" disabled={submitting}>
          {submitting ? "Checking…" : "Enter"}
        </button>
      </form>
    </div>
  );
};

export default Login;
