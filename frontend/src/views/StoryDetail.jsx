import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getStory } from "../api.js";
import { formatTimeAgo } from "../time.js";

const StoryDetail = () => {
  const { id } = useParams();
  const [story, setStory] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getStory(id)
      .then(setStory)
      .catch((err) => setError(err.message));
  }, [id]);

  if (error) {
    return (
      <div id="detail-page">
        <Link className="back-link" to="/">
          ← Back
        </Link>
        <p className="load-error">{error}</p>
      </div>
    );
  }
  if (story === null) {
    return <p className="boot-loading">Loading story…</p>;
  }

  return (
    <div id="detail-page">
      <Link className="back-link" to="/">
        ← Back to top stories
      </Link>
      <div className="detail-card">
        <div className="detail-head">
          <span className="score-badge">{story.score}</span>
          <span className="detail-topic">{story.topic}</span>
        </div>
        <h1 className="detail-headline">{story.headline}</h1>
        <p className="detail-summary">{story.summary}</p>
        <p className="detail-meta">
          {story.item_count} source item{story.item_count === 1 ? "" : "s"} · latest{" "}
          {formatTimeAgo(story.latest_item_at)}
        </p>
      </div>

      <h2 className="sources-title">Sources</h2>
      <ul className="source-list">
        {story.items.map((item) => (
          <li key={item.id} className="source-item">
            <a href={item.url} target="_blank" rel="noreferrer" className="source-link">
              <span className="source-name">
                {item.source_type === "telegram" ? "✈ " : "⌁ "}
                {item.source_name}
              </span>
              <span className="source-time">{formatTimeAgo(item.published_at)}</span>
              {item.title && <span className="source-headline">{item.title}</span>}
              <span className="source-text">{item.text}</span>
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default StoryDetail;
