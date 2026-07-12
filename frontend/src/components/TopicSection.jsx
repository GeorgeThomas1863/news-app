import { useEffect, useState } from "react";

import { getTopicStories } from "../api.js";
import StoryCard from "./StoryCard.jsx";
import StoryRow from "./StoryRow.jsx";

const COLLAPSED_COUNT = 3;
const SHOW_MORE_BATCH = 5;

const TopicSection = ({ topic }) => {
  const [expanded, setExpanded] = useState(false);
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
    <section className={expanded ? "topic-tile open" : "topic-tile"}>
      <div className="tile-head" onClick={() => setExpanded(!expanded)}>
        <span className="tile-dot" />
        <span className="tile-name">
          {topic.topic}
          <span className="tile-chip">{topic.total}</span>
        </span>
        <span className="tile-chevron" />
      </div>
      {expanded ? (
        <ExpandedStories
          topic={topic}
          stories={stories}
          hasMore={hasMore}
          loadingMore={loadingMore}
          onLoadMore={loadMore}
        />
      ) : (
        <CollapsedStories topic={topic} stories={stories} />
      )}
    </section>
  );
};

const CollapsedStories = ({ topic, stories }) => {
  if (stories.length === 0) return <p className="topic-empty">No stories yet</p>;

  const shown = stories.slice(0, COLLAPSED_COUNT);
  const hiddenCount = topic.total - shown.length;
  return (
    <div className="tile-list">
      {shown.map((story) => (
        <StoryRow key={story.id} story={story} />
      ))}
      {hiddenCount > 0 && <p className="tile-more">+{hiddenCount} more</p>}
    </div>
  );
};

const ExpandedStories = ({ topic, stories, hasMore, loadingMore, onLoadMore }) => {
  if (stories.length === 0) return <p className="topic-empty">No stories yet</p>;

  const remainingCount = topic.total - stories.length;
  return (
    <div className="tile-cards">
      {stories.map((story) => (
        <StoryCard key={story.id} story={story} />
      ))}
      {hasMore && (
        <button className="show-more-btn" onClick={onLoadMore} disabled={loadingMore}>
          {loadingMore ? "Loading…" : `Show more (${remainingCount} more)`}
        </button>
      )}
    </div>
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
