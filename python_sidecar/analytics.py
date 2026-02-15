"""
Analytics module - Compute statistics from scraped tweet data.
Provides frequency analysis, engagement metrics, posting patterns, etc.
"""

import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import Counter, defaultdict


def compute_analytics(tweets_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute comprehensive analytics from tweet data.

    Args:
        tweets_data: List of tweet dicts (from Tweet.to_dict())

    Returns:
        Dict with analytics results
    """
    if not tweets_data:
        return {"summary": "No tweets to analyze"}

    result = {
        "total_tweets": len(tweets_data),
        "date_range": _get_date_range(tweets_data),
        "frequency": _compute_frequency(tweets_data),
        "posting_times": _compute_posting_times(tweets_data),
        "engagement": _compute_engagement_stats(tweets_data),
        "content": _compute_content_stats(tweets_data),
        "hashtags": _get_top_hashtags(tweets_data),
        "mentions": _get_top_mentions(tweets_data),
    }

    return result


def _parse_date(date_val) -> Optional[datetime]:
    """Parse a date value that could be string or datetime"""
    if isinstance(date_val, datetime):
        return date_val
    if isinstance(date_val, str) and date_val:
        try:
            return datetime.fromisoformat(date_val.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            pass
    return None


def _get_date_range(tweets: List[Dict]) -> Dict[str, Any]:
    """Get the date range of tweets"""
    dates = []
    for t in tweets:
        d = _parse_date(t.get("date"))
        if d:
            dates.append(d)

    if not dates:
        return {"start": None, "end": None, "days_span": 0}

    dates.sort()
    return {
        "start": dates[0].isoformat(),
        "end": dates[-1].isoformat(),
        "days_span": (dates[-1] - dates[0]).days,
    }


def _compute_frequency(tweets: List[Dict]) -> Dict[str, Any]:
    """Compute tweet frequency by day, week, month"""
    daily = Counter()
    weekly = Counter()
    monthly = Counter()

    for t in tweets:
        d = _parse_date(t.get("date"))
        if d:
            daily[d.strftime("%Y-%m-%d")] += 1
            weekly[d.strftime("%Y-W%W")] += 1
            monthly[d.strftime("%Y-%m")] += 1

    total_days = len(daily) if daily else 1

    return {
        "daily": dict(daily.most_common()),
        "weekly": dict(weekly.most_common()),
        "monthly": dict(monthly.most_common()),
        "avg_per_day": round(len(tweets) / max(total_days, 1), 2),
        "most_active_day": daily.most_common(1)[0] if daily else None,
    }


def _compute_posting_times(tweets: List[Dict]) -> Dict[str, Any]:
    """Compute posting time patterns (hour x day_of_week heatmap)"""
    hour_counts = Counter()
    dow_counts = Counter()
    heatmap = defaultdict(lambda: defaultdict(int))

    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    for t in tweets:
        d = _parse_date(t.get("date"))
        if d:
            hour = d.hour
            dow = d.weekday()
            hour_counts[hour] += 1
            dow_counts[day_names[dow]] += 1
            heatmap[day_names[dow]][hour] += 1

    # Convert heatmap to serializable format
    heatmap_data = []
    for day in day_names:
        for hour in range(24):
            count = heatmap[day][hour]
            if count > 0:
                heatmap_data.append({"day": day, "hour": hour, "count": count})

    peak_hour = hour_counts.most_common(1)[0][0] if hour_counts else 0
    peak_day = dow_counts.most_common(1)[0][0] if dow_counts else "N/A"

    return {
        "by_hour": dict(sorted(hour_counts.items())),
        "by_day_of_week": dict(dow_counts),
        "heatmap": heatmap_data,
        "peak_hour": peak_hour,
        "peak_day": peak_day,
    }


def _compute_engagement_stats(tweets: List[Dict]) -> Dict[str, Any]:
    """Compute engagement statistics"""
    likes = [t.get("likes", 0) for t in tweets]
    retweets = [t.get("retweets", 0) for t in tweets]
    replies_list = [t.get("replies", 0) for t in tweets]
    views = [t.get("views", 0) for t in tweets]

    def _stats(values):
        if not values:
            return {"total": 0, "avg": 0, "max": 0, "min": 0, "median": 0}
        sorted_v = sorted(values)
        n = len(sorted_v)
        median = sorted_v[n // 2] if n % 2 == 1 else (sorted_v[n // 2 - 1] + sorted_v[n // 2]) / 2
        return {
            "total": sum(values),
            "avg": round(sum(values) / n, 2),
            "max": max(values),
            "min": min(values),
            "median": median,
        }

    # Top tweets by engagement
    scored_tweets = []
    for t in tweets:
        score = t.get("likes", 0) + t.get("retweets", 0) * 2 + t.get("replies", 0)
        scored_tweets.append({"id": t.get("id"), "text": (t.get("text", "")[:100]), "score": score})
    scored_tweets.sort(key=lambda x: x["score"], reverse=True)

    return {
        "likes": _stats(likes),
        "retweets": _stats(retweets),
        "replies": _stats(replies_list),
        "views": _stats(views),
        "top_tweets": scored_tweets[:10],
    }


def _compute_content_stats(tweets: List[Dict]) -> Dict[str, Any]:
    """Compute content-related statistics"""
    texts = [t.get("text", "") for t in tweets]
    text_lengths = [len(t) for t in texts]

    media_count = sum(1 for t in tweets if t.get("media_urls"))
    article_count = sum(1 for t in tweets if t.get("has_article"))

    # Thread detection (simplified - tweets with very long text)
    long_tweets = sum(1 for t in texts if len(t) > 280)

    avg_length = round(sum(text_lengths) / max(len(text_lengths), 1), 1)

    return {
        "avg_text_length": avg_length,
        "max_text_length": max(text_lengths) if text_lengths else 0,
        "min_text_length": min(text_lengths) if text_lengths else 0,
        "media_tweet_count": media_count,
        "media_percentage": round(media_count / max(len(tweets), 1) * 100, 1),
        "article_count": article_count,
        "long_tweet_count": long_tweets,
        "empty_text_count": sum(1 for t in texts if not t.strip()),
    }


def _get_top_hashtags(tweets: List[Dict], top_n: int = 20) -> List[Dict[str, Any]]:
    """Extract and count top hashtags"""
    hashtag_counter = Counter()
    for t in tweets:
        text = t.get("text", "")
        hashtags = re.findall(r"#(\w+)", text)
        for tag in hashtags:
            hashtag_counter[tag.lower()] += 1

    return [{"tag": tag, "count": count} for tag, count in hashtag_counter.most_common(top_n)]


def _get_top_mentions(tweets: List[Dict], top_n: int = 20) -> List[Dict[str, Any]]:
    """Extract and count top mentions"""
    mention_counter = Counter()
    for t in tweets:
        text = t.get("text", "")
        mentions = re.findall(r"@(\w+)", text)
        for mention in mentions:
            mention_counter[mention.lower()] += 1

    return [{"user": user, "count": count} for user, count in mention_counter.most_common(top_n)]
