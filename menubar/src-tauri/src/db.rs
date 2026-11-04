use std::path::Path;

use rusqlite::{params, Connection};
use uuid::Uuid;

#[derive(Debug, Clone, serde::Serialize)]
pub struct Topic {
    pub id: String,
    pub title: String,
    pub created: i64,
    pub memory_count: i64,
    pub preview: Option<String>,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct Memory {
    pub id: String,
    pub body: String,
    pub status: String,
    pub app_id: Option<String>,
    pub topic_id: Option<String>,
    pub conversation_id: Option<String>,
    pub created: i64,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct MemoryDetail {
    #[serde(flatten)]
    pub memory: Memory,
    pub topic_title: Option<String>,
    pub related: Vec<Memory>,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct HomeSummary {
    pub about_count: i64,
    pub about_preview: Option<String>,
    pub topic_count: i64,
    pub topic_preview: Option<String>,
    pub conversation_count: i64,
    pub conversation_preview: Option<String>,
}

pub struct Store {
    conn: Connection,
}

impl Store {
    pub fn open(path: &Path) -> Result<Self, String> {
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
        }
        let conn = Connection::open(path).map_err(|e| e.to_string())?;
        conn.execute_batch(
            "PRAGMA journal_mode = WAL;
             PRAGMA busy_timeout = 5000;
             PRAGMA foreign_keys = ON;",
        )
        .map_err(|e| e.to_string())?;
        let store = Self { conn };
        store.migrate()?;
        Ok(store)
    }

    fn migrate(&self) -> Result<(), String> {
        self.conn
            .execute_batch(
                "CREATE TABLE IF NOT EXISTS connected_apps (
                    app_id TEXT PRIMARY KEY,
                    connected INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS topics (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    app_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    body TEXT NOT NULL,
                    status TEXT NOT NULL,
                    app_id TEXT,
                    topic_id TEXT,
                    conversation_id TEXT,
                    created INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS memory_links (
                    from_id TEXT NOT NULL,
                    to_id TEXT NOT NULL,
                    PRIMARY KEY (from_id, to_id)
                );",
            )
            .map_err(|e| e.to_string())?;
        Ok(())
    }

    pub fn set_connected(&self, app_id: &str, connected: bool) -> Result<(), String> {
        self.conn
            .execute(
                "INSERT INTO connected_apps (app_id, connected) VALUES (?1, ?2)
                 ON CONFLICT(app_id) DO UPDATE SET connected = excluded.connected",
                params![app_id, if connected { 1 } else { 0 }],
            )
            .map_err(|e| e.to_string())?;
        Ok(())
    }

    pub fn connected_ids(&self) -> Result<Vec<String>, String> {
        let mut stmt = self
            .conn
            .prepare("SELECT app_id FROM connected_apps WHERE connected = 1 ORDER BY app_id")
            .map_err(|e| e.to_string())?;
        let rows = stmt
            .query_map([], |row| row.get(0))
            .map_err(|e| e.to_string())?;
        rows.collect::<Result<Vec<_>, _>>().map_err(|e| e.to_string())
    }

    pub fn list_topics(&self, query: &str) -> Result<Vec<Topic>, String> {
        let like = like_pattern(query);
        let mut stmt = self
            .conn
            .prepare(
                "SELECT t.id, t.title, t.created,
                        (SELECT COUNT(*) FROM memories m WHERE m.topic_id = t.id),
                        (SELECT body FROM memories m WHERE m.topic_id = t.id ORDER BY m.created DESC LIMIT 1)
                 FROM topics t
                 WHERE (?1 = '' OR t.title LIKE ?1 ESCAPE '\\')
                 ORDER BY t.created DESC",
            )
            .map_err(|e| e.to_string())?;
        let rows = stmt
            .query_map(params![like], |row| {
                Ok(Topic {
                    id: row.get(0)?,
                    title: row.get(1)?,
                    created: row.get(2)?,
                    memory_count: row.get(3)?,
                    preview: row.get(4)?,
                })
            })
            .map_err(|e| e.to_string())?;
        rows.collect::<Result<Vec<_>, _>>().map_err(|e| e.to_string())
    }

    pub fn create_topic(&self, title: &str) -> Result<Topic, String> {
        let title = title.trim();
        if title.is_empty() {
            return Err("Topic needs a title".into());
        }
        let id = Uuid::new_v4().to_string();
        let created = now_ms();
        self.conn
            .execute(
                "INSERT INTO topics (id, title, created) VALUES (?1, ?2, ?3)",
                params![id, title, created],
            )
            .map_err(|e| e.to_string())?;
        Ok(Topic {
            id,
            title: title.to_string(),
            created,
            memory_count: 0,
            preview: None,
        })
    }

    pub fn list_memories(
        &self,
        query: &str,
        topic_id: Option<&str>,
        about_you: bool,
        app_id: Option<&str>,
        limit: i64,
    ) -> Result<Vec<Memory>, String> {
        let like = like_pattern(query);
        let mut stmt = self
            .conn
            .prepare(
                "SELECT id, body, status, app_id, topic_id, conversation_id, created
                 FROM memories
                 WHERE (?1 = '' OR body LIKE ?1 ESCAPE '\\')
                   AND (?2 IS NULL OR topic_id = ?2)
                   AND (?3 = 0 OR (topic_id IS NULL AND conversation_id IS NULL))
                   AND (?4 IS NULL OR app_id = ?4)
                 ORDER BY created DESC
                 LIMIT ?5",
            )
            .map_err(|e| e.to_string())?;
        let rows = stmt
            .query_map(
                params![
                    like,
                    topic_id,
                    if about_you { 1 } else { 0 },
                    app_id,
                    limit
                ],
                read_memory,
            )
            .map_err(|e| e.to_string())?;
        rows.collect::<Result<Vec<_>, _>>().map_err(|e| e.to_string())
    }

    pub fn create_memory(
        &self,
        body: &str,
        topic_id: Option<&str>,
        app_id: Option<&str>,
    ) -> Result<Memory, String> {
        let body = body.trim();
        if body.is_empty() {
            return Err("Memory needs a sentence".into());
        }
        if let Some(topic_id) = topic_id {
            let exists: i64 = self
                .conn
                .query_row(
                    "SELECT COUNT(*) FROM topics WHERE id = ?1",
                    params![topic_id],
                    |row| row.get(0),
                )
                .map_err(|e| e.to_string())?;
            if exists == 0 {
                return Err("Topic not found".into());
            }
        }
        let id = Uuid::new_v4().to_string();
        let created = now_ms();
        self.conn
            .execute(
                "INSERT INTO memories (id, body, status, app_id, topic_id, conversation_id, created)
                 VALUES (?1, ?2, 'settled', ?3, ?4, NULL, ?5)",
                params![id, body, app_id, topic_id, created],
            )
            .map_err(|e| e.to_string())?;
        Ok(Memory {
            id,
            body: body.to_string(),
            status: "settled".into(),
            app_id: app_id.map(str::to_string),
            topic_id: topic_id.map(str::to_string),
            conversation_id: None,
            created,
        })
    }

    pub fn get_memory(&self, id: &str) -> Result<MemoryDetail, String> {
        let memory = self
            .conn
            .query_row(
                "SELECT id, body, status, app_id, topic_id, conversation_id, created
                 FROM memories WHERE id = ?1",
                params![id],
                read_memory,
            )
            .map_err(|_| "Memory not found".to_string())?;
        let topic_title = if let Some(topic_id) = &memory.topic_id {
            self.conn
                .query_row(
                    "SELECT title FROM topics WHERE id = ?1",
                    params![topic_id],
                    |row| row.get(0),
                )
                .ok()
        } else {
            None
        };
        let mut stmt = self
            .conn
            .prepare(
                "SELECT m.id, m.body, m.status, m.app_id, m.topic_id, m.conversation_id, m.created
                 FROM memories m
                 JOIN memory_links l
                   ON (l.from_id = ?1 AND l.to_id = m.id)
                   OR (l.to_id = ?1 AND l.from_id = m.id)
                 ORDER BY m.created DESC",
            )
            .map_err(|e| e.to_string())?;
        let related = stmt
            .query_map(params![id], read_memory)
            .map_err(|e| e.to_string())?
            .collect::<Result<Vec<_>, _>>()
            .map_err(|e| e.to_string())?;
        Ok(MemoryDetail {
            memory,
            topic_title,
            related,
        })
    }

    pub fn link_memories(&self, from_id: &str, to_id: &str) -> Result<(), String> {
        if from_id == to_id {
            return Err("A memory cannot relate to itself".into());
        }
        let count: i64 = self
            .conn
            .query_row(
                "SELECT COUNT(*) FROM memories WHERE id IN (?1, ?2)",
                params![from_id, to_id],
                |row| row.get(0),
            )
            .map_err(|e| e.to_string())?;
        if count != 2 {
            return Err("Both memories need to exist".into());
        }
        let (a, b) = if from_id < to_id {
            (from_id, to_id)
        } else {
            (to_id, from_id)
        };
        self.conn
            .execute(
                "INSERT OR IGNORE INTO memory_links (from_id, to_id) VALUES (?1, ?2)",
                params![a, b],
            )
            .map_err(|e| e.to_string())?;
        Ok(())
    }

    pub fn home_summary(&self, connected_names: &[String]) -> Result<HomeSummary, String> {
        let about_count: i64 = self
            .conn
            .query_row(
                "SELECT COUNT(*) FROM memories WHERE topic_id IS NULL AND conversation_id IS NULL",
                [],
                |row| row.get(0),
            )
            .map_err(|e| e.to_string())?;
        let about_preview: Option<String> = self
            .conn
            .query_row(
                "SELECT body FROM memories
                 WHERE topic_id IS NULL AND conversation_id IS NULL
                 ORDER BY created DESC LIMIT 1",
                [],
                |row| row.get(0),
            )
            .ok();
        let topic_count: i64 = self
            .conn
            .query_row("SELECT COUNT(*) FROM topics", [], |row| row.get(0))
            .map_err(|e| e.to_string())?;
        let topic_preview: Option<String> = self
            .conn
            .query_row(
                "SELECT title FROM topics ORDER BY created DESC LIMIT 1",
                [],
                |row| row.get(0),
            )
            .ok();
        Ok(HomeSummary {
            about_count,
            about_preview,
            topic_count,
            topic_preview,
            conversation_count: connected_names.len() as i64,
            conversation_preview: connected_names.first().cloned(),
        })
    }
}

fn read_memory(row: &rusqlite::Row<'_>) -> rusqlite::Result<Memory> {
    Ok(Memory {
        id: row.get(0)?,
        body: row.get(1)?,
        status: row.get(2)?,
        app_id: row.get(3)?,
        topic_id: row.get(4)?,
        conversation_id: row.get(5)?,
        created: row.get(6)?,
    })
}

fn like_pattern(query: &str) -> String {
    let q = query.trim();
    if q.is_empty() {
        return String::new();
    }
    let escaped = q
        .replace('\\', "\\\\")
        .replace('%', "\\%")
        .replace('_', "\\_");
    format!("%{escaped}%")
}

fn now_ms() -> i64 {
    use std::time::{SystemTime, UNIX_EPOCH};
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis() as i64)
        .unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn temp_store() -> Store {
        let path = std::env::temp_dir().join(format!("memory-test-{}.db", Uuid::new_v4()));
        Store::open(&path).unwrap()
    }

    #[test]
    fn topic_and_memory_roundtrip() {
        let store = temp_store();
        let topic = store.create_topic("Coffee").unwrap();
        let memory = store
            .create_memory("Use 18g in", Some(&topic.id), Some("cursor"))
            .unwrap();
        let listed = store
            .list_memories("18g", Some(&topic.id), false, None, 20)
            .unwrap();
        assert_eq!(listed.len(), 1);
        assert_eq!(listed[0].id, memory.id);
        let about = store.list_memories("", None, true, None, 20).unwrap();
        assert!(about.is_empty());
    }

    #[test]
    fn links_are_bidirectional() {
        let store = temp_store();
        let a = store.create_memory("Prefers short answers", None, None).unwrap();
        let b = store.create_memory("Writes in English", None, None).unwrap();
        store.link_memories(&a.id, &b.id).unwrap();
        let detail = store.get_memory(&b.id).unwrap();
        assert_eq!(detail.related.len(), 1);
        assert_eq!(detail.related[0].id, a.id);
    }
}
