import { Link } from "react-router-dom";

import { getScoreBand } from "../score.js";
import { formatTimeAgo } from "../time.js";

const StoryRow = ({ story }) => {
  return (
    <Link className="story-row" to={`/story/${story.id}`}>
      <span className={`score-badge ${getScoreBand(story.score)}`}>{story.score}</span>
      <span className="row-headline">{story.headline}</span>
      <span className="row-time">{formatTimeAgo(story.latest_item_at)}</span>
    </Link>
  );
};

export default StoryRow;
