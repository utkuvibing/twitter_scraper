"""
AI Analyzer - OpenAI API integration for tweet analysis.
Provides sentiment analysis, topic extraction, style analysis, and recommendations.
Uses the user's own OpenAI API key.
"""

import json
from typing import List, Dict, Any, Optional


class AIAnalyzer:
    """Analyzes tweets using OpenAI API"""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self._client = None

    def _get_client(self):
        """Lazy-initialize OpenAI client"""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "openai package is required for AI analysis. "
                    "Install it with: pip install openai"
                )
        return self._client

    def analyze(self, tweets_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run full analysis on tweet data.

        Returns dict with sentiment, topics, style, recommendations, summary.
        """
        # Prepare tweet texts for analysis
        texts = []
        for t in tweets_data[:200]:  # Limit to 200 tweets to manage token usage
            text = t.get("text", "").strip()
            if text:
                date_str = t.get("date_str", "")
                likes = t.get("likes", 0)
                rts = t.get("retweets", 0)
                texts.append(f"[{date_str}] (Likes: {likes}, RTs: {rts}) {text}")

        if not texts:
            return {"summary": "No tweet text available for analysis"}

        combined_text = "\n---\n".join(texts[:100])  # First 100 for main analysis

        result = {}

        # Run analyses
        result["sentiment"] = self._analyze_sentiment(combined_text)
        result["topics"] = self._extract_topics(combined_text)
        result["style"] = self._analyze_style(combined_text)
        result["recommendations"] = self._get_recommendations(combined_text, tweets_data)
        result["summary"] = self._generate_summary(combined_text, tweets_data)

        return result

    def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        """Make an OpenAI API call and return the response text"""
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=1000,
        )
        return response.choices[0].message.content

    def _analyze_sentiment(self, tweets_text: str) -> Dict[str, Any]:
        """Analyze sentiment distribution"""
        system = (
            "You are a sentiment analysis expert. Analyze the following tweets and provide "
            "a sentiment breakdown. Return ONLY valid JSON with this format: "
            '{"positive": <percentage>, "negative": <percentage>, "neutral": <percentage>, '
            '"dominant_emotion": "<emotion>", "overall": "<positive/negative/neutral>"}'
        )
        try:
            response = self._call_openai(system, f"Analyze sentiment of these tweets:\n\n{tweets_text}")
            # Try to parse JSON from response
            return self._parse_json_response(response)
        except Exception as e:
            return {"error": str(e)}

    def _extract_topics(self, tweets_text: str) -> List[str]:
        """Extract main topics/themes"""
        system = (
            "You are a content analysis expert. Extract the main topics and themes from "
            "the following tweets. Return ONLY valid JSON array of topic strings, max 10 topics. "
            'Example: ["Technology", "AI/ML", "Startup culture"]'
        )
        try:
            response = self._call_openai(system, f"Extract topics from these tweets:\n\n{tweets_text}")
            result = self._parse_json_response(response)
            return result if isinstance(result, list) else []
        except Exception as e:
            return [f"Error: {e}"]

    def _analyze_style(self, tweets_text: str) -> str:
        """Analyze writing style"""
        system = (
            "You are a writing style analyst. Analyze the tweeting style and patterns. "
            "Describe in 2-3 sentences: tone, format preferences (short/long, threads, questions), "
            "language level, and any distinctive patterns."
        )
        try:
            return self._call_openai(system, f"Analyze the writing style:\n\n{tweets_text}")
        except Exception as e:
            return f"Error: {e}"

    def _get_recommendations(self, tweets_text: str, tweets_data: List[Dict]) -> List[str]:
        """Generate content strategy recommendations"""
        # Add engagement context
        total = len(tweets_data)
        avg_likes = sum(t.get("likes", 0) for t in tweets_data) / max(total, 1)
        avg_rts = sum(t.get("retweets", 0) for t in tweets_data) / max(total, 1)

        context = (
            f"Total tweets: {total}, Avg likes: {avg_likes:.0f}, Avg retweets: {avg_rts:.0f}"
        )

        system = (
            "You are a social media strategy expert. Based on the tweet data and engagement metrics, "
            "provide 3-5 actionable content strategy recommendations. "
            "Return ONLY a valid JSON array of recommendation strings."
        )
        try:
            response = self._call_openai(
                system,
                f"Context: {context}\n\nTweets:\n{tweets_text}"
            )
            result = self._parse_json_response(response)
            return result if isinstance(result, list) else []
        except Exception as e:
            return [f"Error: {e}"]

    def _generate_summary(self, tweets_text: str, tweets_data: List[Dict]) -> str:
        """Generate an executive summary"""
        total = len(tweets_data)
        media_count = sum(1 for t in tweets_data if t.get("media_urls"))

        context = (
            f"Total tweets analyzed: {total}, "
            f"Tweets with media: {media_count}"
        )

        system = (
            "You are a social media analyst. Write a concise executive summary (3-5 sentences) "
            "of this Twitter/X account's activity, content themes, and engagement patterns."
        )
        try:
            return self._call_openai(
                system,
                f"Context: {context}\n\nSample tweets:\n{tweets_text}"
            )
        except Exception as e:
            return f"Error generating summary: {e}"

    def compare_profiles(
        self,
        profile_a_tweets: List[Dict],
        profile_b_tweets: List[Dict],
        profile_a_name: str = "Profile A",
        profile_b_name: str = "Profile B",
    ) -> Dict[str, Any]:
        """Compare two profiles side by side"""
        texts_a = "\n---\n".join(
            t.get("text", "")[:200] for t in profile_a_tweets[:50] if t.get("text")
        )
        texts_b = "\n---\n".join(
            t.get("text", "")[:200] for t in profile_b_tweets[:50] if t.get("text")
        )

        system = (
            "You are a social media comparison analyst. Compare these two Twitter profiles "
            "and return a JSON object with: "
            '{"similarities": ["..."], "differences": ["..."], '
            '"profile_a_strengths": ["..."], "profile_b_strengths": ["..."], '
            '"recommendation": "..."}'
        )
        try:
            response = self._call_openai(
                system,
                f"{profile_a_name} tweets:\n{texts_a}\n\n"
                f"{profile_b_name} tweets:\n{texts_b}",
            )
            return self._parse_json_response(response)
        except Exception as e:
            return {"error": str(e)}

    def _parse_json_response(self, response: str) -> Any:
        """Try to parse JSON from an OpenAI response, handling markdown code blocks"""
        response = response.strip()
        # Remove markdown code blocks if present
        if response.startswith("```"):
            lines = response.split("\n")
            lines = lines[1:]  # Remove first ``` line
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response = "\n".join(lines)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to find JSON in the response
            import re
            json_match = re.search(r'[\[{].*[\]}]', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            return response
