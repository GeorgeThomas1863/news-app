import { useCallback, useEffect, useState } from "react";

import { getStories } from "../api.js";
import Header from "../components/Header.jsx";
import TopicSection from "../components/TopicSection.jsx";

const Main = ({ onLogout }) => {
  const [topics, setTopics] = useState(null);
  const [error, setError] = useState(null);

  const loadStories = useCallback(async () => {
    try {
      const body = await getStories();
      setTopics(body.topics);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    loadStories();
  }, [loadStories]);

  return (
    <div id="main-page">
      <Header onRefreshed={loadStories} onLogout={onLogout} />
      {error && <p className="load-error">{error}</p>}
      {topics === null && !error && <p className="boot-loading">Loading stories…</p>}
      {topics && (
        <div id="topics-wrapper">
          {topics.map((topic) => (
            <TopicSection key={topic.topic} topic={topic} />
          ))}
        </div>
      )}
    </div>
  );
};

export default Main;
