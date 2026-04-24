BASE_PARSING_COST = 2
VIDEO_COST = 1
MAX_VIDEOS_PER_PARSING = 500


def get_start_parsing_cost() -> int:
    return BASE_PARSING_COST


def get_video_parsing_cost(videos_count: int) -> int:
    return videos_count * VIDEO_COST


def get_max_videos_limit() -> int:
    return MAX_VIDEOS_PER_PARSING