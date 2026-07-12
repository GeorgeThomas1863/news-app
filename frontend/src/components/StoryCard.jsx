import { Link } from "react-router-dom";

import { getScoreBand } from "../score.js";
import { formatTimeAgo } from "../time.js";

const StoryCard = ({ story }) => {
  return (
    <Link className="story-card" to={`/story/${story.id}`}>
      <div className="story-card-top">
        <span className={`score-badge ${getScoreBand(story.score)}`}>{story.score}</span>
        <h3 className="story-headline">{story.headline}</h3>
      </div>
      <p className="story-summary">{story.summary}</p>
      <p className="story-meta">
        {story.item_count} source{story.item_count === 1 ? "" : "s"} ·{" "}
        {formatTimeAgo(story.latest_item_at)}
      </p>
    </Link>
  );
};

export default StoryCard;
