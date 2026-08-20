import { useState } from "react";

import { login } from "../api.js";
import flagUrl from "../assets/freedom1.jpg";

const EYE_CLOSED_ICON = (
  <svg
    aria-hidden="true"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
    <circle cx="12" cy="12" r="3" />
    <path d="M2 2l20 20" />
  </svg>
);

const EYE_OPEN_ICON = (
  <svg
    aria-hidden="true"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
);

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
      <img id="auth-background-pic" src={flagUrl} alt="" />
      <form id="auth-form-wrapper" onSubmit={submitPassword}>
        <label id="auth-label" htmlFor="auth-pw">
          Welcome to the News Machine
        </label>
        <div className="password-input-wrapper">
          <input
            id="auth-pw"
            className="password-input"
            type={showPassword ? "text" : "password"}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoFocus
          />
          <button
            type="button"
            className="password-toggle-btn"
            aria-label={showPassword ? "Hide password" : "Show password"}
            onClick={() => setShowPassword(!showPassword)}
          >
            {showPassword ? EYE_OPEN_ICON : EYE_CLOSED_ICON}
          </button>
        </div>
        {error && <p className="auth-error">{error}</p>}
        <button className="btn-submit" type="submit" disabled={submitting}>
          {submitting ? "Checking…" : "Submit"}
        </button>
      </form>
    </div>
  );
};

export default Login;
