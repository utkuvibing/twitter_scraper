use crate::commands::analytics::ScrapeRecord;
use rusqlite::{params, Connection, Result};
use std::collections::HashMap;

pub struct Database {
    conn: Connection,
}

impl Database {
    pub fn new() -> Result<Self> {
        let db_path = Self::get_db_path();
        // Ensure parent directory exists
        if let Some(parent) = std::path::Path::new(&db_path).parent() {
            std::fs::create_dir_all(parent).ok();
        }
        let conn = Connection::open(&db_path)?;
        conn.execute_batch("PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;")?;
        Ok(Database { conn })
    }

    fn get_db_path() -> String {
        if let Some(data_dir) = dirs::data_local_dir() {
            let app_dir = data_dir.join("twitter-x-scraper");
            std::fs::create_dir_all(&app_dir).ok();
            app_dir
                .join("scraper.db")
                .to_string_lossy()
                .to_string()
        } else {
            "scraper.db".to_string()
        }
    }

    pub fn run_migrations(&self) -> Result<()> {
        self.conn.execute_batch(
            "
            CREATE TABLE IF NOT EXISTS scrapes (
                id TEXT PRIMARY KEY,
                target_username TEXT NOT NULL,
                scrape_type TEXT NOT NULL,
                mode TEXT NOT NULL,
                started_at DATETIME NOT NULL DEFAULT (datetime('now')),
                completed_at DATETIME,
                tweet_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'running'
            );

            CREATE TABLE IF NOT EXISTS tweets (
                id TEXT PRIMARY KEY,
                scrape_id TEXT NOT NULL,
                text TEXT,
                date DATETIME,
                date_str TEXT,
                tweet_url TEXT,
                media_urls TEXT,
                has_article BOOLEAN DEFAULT FALSE,
                likes INTEGER DEFAULT 0,
                retweets INTEGER DEFAULT 0,
                replies INTEGER DEFAULT 0,
                views INTEGER DEFAULT 0,
                FOREIGN KEY (scrape_id) REFERENCES scrapes(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE TABLE IF NOT EXISTS schedules (
                id TEXT PRIMARY KEY,
                target_username TEXT NOT NULL,
                scrape_type TEXT NOT NULL,
                mode TEXT NOT NULL,
                mode_config TEXT,
                cron_expression TEXT,
                last_run DATETIME,
                next_run DATETIME,
                enabled BOOLEAN DEFAULT TRUE
            );

            CREATE INDEX IF NOT EXISTS idx_tweets_scrape_id ON tweets(scrape_id);
            CREATE INDEX IF NOT EXISTS idx_scrapes_status ON scrapes(status);
            CREATE INDEX IF NOT EXISTS idx_scrapes_target ON scrapes(target_username);
            ",
        )?;
        Ok(())
    }

    // ─── Scrapes ───────────────────────────────────────────

    pub fn insert_scrape(
        &self,
        id: &str,
        target_username: &str,
        scrape_type: &str,
        mode: &str,
    ) -> Result<()> {
        self.conn.execute(
            "INSERT INTO scrapes (id, target_username, scrape_type, mode) VALUES (?1, ?2, ?3, ?4)",
            params![id, target_username, scrape_type, mode],
        )?;
        Ok(())
    }

    pub fn update_scrape_status(
        &self,
        id: &str,
        status: &str,
        tweet_count: i64,
    ) -> Result<()> {
        if status == "completed" || status == "error" || status == "cancelled" {
            self.conn.execute(
                "UPDATE scrapes SET status = ?1, tweet_count = ?2, completed_at = datetime('now') WHERE id = ?3",
                params![status, tweet_count, id],
            )?;
        } else {
            self.conn.execute(
                "UPDATE scrapes SET status = ?1, tweet_count = ?2 WHERE id = ?3",
                params![status, tweet_count, id],
            )?;
        }
        Ok(())
    }

    pub fn get_scrape_history(&self) -> Result<Vec<ScrapeRecord>> {
        let mut stmt = self.conn.prepare(
            "SELECT id, target_username, scrape_type, mode, started_at, completed_at, tweet_count, status
             FROM scrapes ORDER BY started_at DESC LIMIT 100",
        )?;

        let records = stmt
            .query_map([], |row| {
                Ok(ScrapeRecord {
                    id: row.get(0)?,
                    target_username: row.get(1)?,
                    scrape_type: row.get(2)?,
                    mode: row.get(3)?,
                    started_at: row.get(4)?,
                    completed_at: row.get(5)?,
                    tweet_count: row.get(6)?,
                    status: row.get(7)?,
                })
            })?
            .collect::<Result<Vec<_>>>()?;

        Ok(records)
    }

    pub fn delete_scrape(&self, id: &str) -> Result<()> {
        self.conn
            .execute("DELETE FROM tweets WHERE scrape_id = ?1", params![id])?;
        self.conn
            .execute("DELETE FROM scrapes WHERE id = ?1", params![id])?;
        Ok(())
    }

    // ─── Tweets ────────────────────────────────────────────

    pub fn insert_tweet(
        &self,
        id: &str,
        scrape_id: &str,
        text: &str,
        date: Option<&str>,
        date_str: &str,
        tweet_url: &str,
        media_urls: &str,
        has_article: bool,
        likes: i64,
        retweets: i64,
        replies: i64,
        views: i64,
    ) -> Result<()> {
        self.conn.execute(
            "INSERT OR REPLACE INTO tweets (id, scrape_id, text, date, date_str, tweet_url, media_urls, has_article, likes, retweets, replies, views)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12)",
            params![id, scrape_id, text, date, date_str, tweet_url, media_urls, has_article, likes, retweets, replies, views],
        )?;
        Ok(())
    }

    pub fn get_tweets_for_scrape(&self, scrape_id: &str) -> Result<Vec<serde_json::Value>> {
        let mut stmt = self.conn.prepare(
            "SELECT id, text, date, date_str, tweet_url, media_urls, has_article, likes, retweets, replies, views
             FROM tweets WHERE scrape_id = ?1 ORDER BY date DESC",
        )?;

        let tweets = stmt
            .query_map(params![scrape_id], |row| {
                let media_str: String = row.get::<_, String>(5).unwrap_or_default();
                let media_urls: Vec<String> = serde_json::from_str(&media_str).unwrap_or_default();

                Ok(serde_json::json!({
                    "id": row.get::<_, String>(0)?,
                    "text": row.get::<_, String>(1).unwrap_or_default(),
                    "date": row.get::<_, Option<String>>(2)?,
                    "date_str": row.get::<_, String>(3).unwrap_or_default(),
                    "tweet_url": row.get::<_, String>(4).unwrap_or_default(),
                    "media_urls": media_urls,
                    "has_article": row.get::<_, bool>(6).unwrap_or(false),
                    "likes": row.get::<_, i64>(7).unwrap_or(0),
                    "retweets": row.get::<_, i64>(8).unwrap_or(0),
                    "replies": row.get::<_, i64>(9).unwrap_or(0),
                    "views": row.get::<_, i64>(10).unwrap_or(0),
                }))
            })?
            .collect::<Result<Vec<_>>>()?;

        Ok(tweets)
    }

    // ─── Settings ──────────────────────────────────────────

    pub fn set_setting(&self, key: &str, value: &str) -> Result<()> {
        self.conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?1, ?2)",
            params![key, value],
        )?;
        Ok(())
    }

    pub fn get_setting(&self, key: &str) -> Result<Option<String>> {
        let mut stmt = self
            .conn
            .prepare("SELECT value FROM settings WHERE key = ?1")?;
        let result = stmt
            .query_row(params![key], |row| row.get(0))
            .ok();
        Ok(result)
    }

    pub fn get_all_settings(&self) -> Result<HashMap<String, String>> {
        let mut stmt = self.conn.prepare("SELECT key, value FROM settings")?;
        let settings = stmt
            .query_map([], |row| {
                Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
            })?
            .collect::<Result<HashMap<_, _>>>()?;
        Ok(settings)
    }

    // ─── Schedules ─────────────────────────────────────────

    pub fn get_active_schedules(&self) -> Result<Vec<serde_json::Value>> {
        let mut stmt = self.conn.prepare(
            "SELECT id, target_username, scrape_type, mode, mode_config, cron_expression, last_run, next_run
             FROM schedules WHERE enabled = TRUE",
        )?;

        let schedules = stmt
            .query_map([], |row| {
                Ok(serde_json::json!({
                    "id": row.get::<_, String>(0)?,
                    "target_username": row.get::<_, String>(1)?,
                    "scrape_type": row.get::<_, String>(2)?,
                    "mode": row.get::<_, String>(3)?,
                    "mode_config": row.get::<_, Option<String>>(4)?,
                    "cron_expression": row.get::<_, Option<String>>(5)?,
                    "last_run": row.get::<_, Option<String>>(6)?,
                    "next_run": row.get::<_, Option<String>>(7)?,
                }))
            })?
            .collect::<Result<Vec<_>>>()?;

        Ok(schedules)
    }
}
