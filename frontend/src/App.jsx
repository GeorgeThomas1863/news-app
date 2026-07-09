import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AUTH_EXPIRED_EVENT, checkAuth } from "./api.js";
import Login from "./views/Login.jsx";
import Main from "./views/Main.jsx";
import StoryDetail from "./views/StoryDetail.jsx";

const App = () => {
  const [authed, setAuthed] = useState(null);

  useEffect(() => {
    const markExpired = () => setAuthed(false);
    window.addEventListener(AUTH_EXPIRED_EVENT, markExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, markExpired);
  }, []);

  useEffect(() => {
    checkAuth()
      .then(() => setAuthed(true))
      .catch(() => setAuthed(false));
  }, []);

  if (authed === null) {
    return <div className="boot-loading">Loading…</div>;
  }
  if (!authed) {
    return <Login onLogin={() => setAuthed(true)} />;
  }

  return (
    <Routes>
      <Route path="/" element={<Main onLogout={() => setAuthed(false)} />} />
      <Route path="/story/:id" element={<StoryDetail />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default App;
