use crate::AppState;
use serde::Serialize;
use tauri::State;

#[derive(Debug, Serialize)]
pub struct ScrapeRecord {
    pub id: String,
    pub target_username: String,
    pub scrape_type: String,
    pub mode: String,
    pub started_at: String,
    pub completed_at: Option<String>,
    pub tweet_count: i64,
    pub status: String,
}

#[tauri::command]
pub async fn get_scrape_history(
    state: State<'_, AppState>,
) -> Result<Vec<ScrapeRecord>, String> {
    let db = state.db.lock().map_err(|e| e.to_string())?;
    db.get_scrape_history().map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn get_tweets_for_scrape(
    state: State<'_, AppState>,
    scrape_id: String,
) -> Result<Vec<serde_json::Value>, String> {
    let db = state.db.lock().map_err(|e| e.to_string())?;
    db.get_tweets_for_scrape(&scrape_id)
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn get_analytics(
    state: State<'_, AppState>,
    scrape_id: String,
) -> Result<serde_json::Value, String> {
    let db = state.db.lock().map_err(|e| e.to_string())?;
    let tweets = db
        .get_tweets_for_scrape(&scrape_id)
        .map_err(|e| e.to_string())?;

    // Return tweets directly - analytics computation happens client-side
    Ok(serde_json::json!({
        "scrape_id": scrape_id,
        "tweet_count": tweets.len(),
        "tweets": tweets,
    }))
}

#[tauri::command]
pub async fn analyze_with_ai(
    state: State<'_, AppState>,
    scrape_id: String,
    api_key: String,
) -> Result<serde_json::Value, String> {
    let db = state.db.lock().map_err(|e| e.to_string())?;
    let tweets = db
        .get_tweets_for_scrape(&scrape_id)
        .map_err(|e| e.to_string())?;

    if tweets.is_empty() {
        return Err("No tweets found for this scrape".to_string());
    }

    // Send to Python sidecar for AI analysis
    let sidecar = state.sidecar.lock().map_err(|e| e.to_string())?;
    let cmd = serde_json::json!({
        "command": "analyze",
        "api_key": api_key,
        "tweets": tweets,
    });
    sidecar
        .send_command(&cmd)
        .map_err(|e| format!("Failed to send AI analysis command: {}", e))?;

    Ok(serde_json::json!({"status": "analysis_started", "tweet_count": tweets.len()}))
}

#[tauri::command]
pub async fn save_scrape_tweets(
    state: State<'_, AppState>,
    scrape_id: String,
    tweets: Vec<serde_json::Value>,
) -> Result<(), String> {
    let db = state.db.lock().map_err(|e| e.to_string())?;

    for tweet in &tweets {
        let id = tweet["id"].as_str().unwrap_or_default();
        let text = tweet["text"].as_str().unwrap_or_default();
        let date = tweet["date_str"].as_str();
        let date_str = tweet["date_str"].as_str().unwrap_or_default();
        let tweet_url = tweet["tweet_url"].as_str().unwrap_or_default();
        let media_urls = serde_json::to_string(
            &tweet["media_urls"].as_array().unwrap_or(&vec![]),
        )
        .unwrap_or_else(|_| "[]".to_string());
        let has_article = tweet["has_article"].as_bool().unwrap_or(false);
        let likes = tweet["likes"].as_i64().unwrap_or(0);
        let retweets = tweet["retweets"].as_i64().unwrap_or(0);
        let replies = tweet["replies"].as_i64().unwrap_or(0);
        let views = tweet["views"].as_i64().unwrap_or(0);

        db.insert_tweet(
            id,
            &scrape_id,
            text,
            date,
            date_str,
            tweet_url,
            &media_urls,
            has_article,
            likes,
            retweets,
            replies,
            views,
        )
        .map_err(|e| format!("Failed to save tweet {}: {}", id, e))?;
    }

    // Update scrape record with final count
    db.update_scrape_status(&scrape_id, "completed", tweets.len() as i64)
        .map_err(|e| e.to_string())?;

    Ok(())
}

#[tauri::command]
pub async fn delete_scrape(
    state: State<'_, AppState>,
    scrape_id: String,
) -> Result<(), String> {
    let db = state.db.lock().map_err(|e| e.to_string())?;
    db.delete_scrape(&scrape_id).map_err(|e| e.to_string())
}
