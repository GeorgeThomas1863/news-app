import { useState } from "react";

import { getTopicStories } from "../api.js";
import StoryCard from "./StoryCard.jsx";

const SHOW_MORE_BATCH = 5;

const TopicSection = ({ topic }) => {
  const [expanded, setExpanded] = useState(true);
  const [stories, setStories] = useState(topic.stories);
  const [loadingMore, setLoadingMore] = useState(false);

  const hasMore = stories.length < topic.total;

  const loadMore = async () => {
    if (loadingMore) return;
    setLoadingMore(true);
    try {
      const body = await getTopicStories(topic.topic, stories.length, SHOW_MORE_BATCH);
      setStories([...stories, ...body.stories]);
    } finally {
      setLoadingMore(false);
    }
  };

  return (
    <section className="topic-section">
      <div className="collapse-header" onClick={() => setExpanded(!expanded)}>
        <span className={expanded ? "collapse-arrow expanded" : "collapse-arrow"} />
        <span className="collapse-title">
          {topic.topic}
          <span className="topic-count">{topic.total}</span>
        </span>
      </div>
      {expanded && (
        <div className="collapse-content">
          {stories.length === 0 && <p className="topic-empty">No stories yet</p>}
          {stories.map((story) => (
            <StoryCard key={story.id} story={story} />
          ))}
          {hasMore && (
            <button className="show-more-btn" onClick={loadMore} disabled={loadingMore}>
              {loadingMore ? "Loading…" : "Show more"}
            </button>
          )}
        </div>
      )}
    </section>
  );
};

export default TopicSection;
