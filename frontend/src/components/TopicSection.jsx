import { useEffect, useState } from "react";

import { getTopicStories } from "../api.js";
import StoryCard from "./StoryCard.jsx";

const SHOW_MORE_BATCH = 5;

const TopicSection = ({ topic }) => {
  const [expanded, setExpanded] = useState(true);
  const [stories, setStories] = useState(topic.stories);
  const [skip, setSkip] = useState(topic.stories.length);
  const [loadingMore, setLoadingMore] = useState(false);

  // Each dashboard refetch re-ranks the topic server-side; discard paged-in
  // extras and restart from the fresh first page.
  useEffect(() => {
    setStories(topic.stories);
    setSkip(topic.stories.length);
  }, [topic]);

  const hasMore = skip < topic.total;

  const loadMore = async () => {
    if (loadingMore) return;
    setLoadingMore(true);
    try {
      const body = await getTopicStories(topic.topic, skip, SHOW_MORE_BATCH);
      setSkip(skip + SHOW_MORE_BATCH);
      setStories(appendNewStories(stories, body.stories));
    } catch (error) {
      console.error("failed to load more stories for topic " + topic.topic, error);
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

// A pipeline run between requests can shift the ranking, so an offset page may
// re-include already-shown stories — drop those to keep StoryCard keys unique.
const appendNewStories = (currentStories, fetchedStories) => {
  const seenIds = new Set();
  for (const story of currentStories) {
    seenIds.add(story.id);
  }

  const merged = [...currentStories];
  for (const story of fetchedStories) {
    if (seenIds.has(story.id)) continue;
    merged.push(story);
  }
  return merged;
};

export default TopicSection;
