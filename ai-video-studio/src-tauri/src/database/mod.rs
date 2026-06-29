pub mod schema;

use rusqlite::{Connection, Result};
use schema::Project;
use std::path::Path;
use std::sync::Mutex;

pub struct Database {
    conn: Mutex<Connection>,
}

impl Database {
    pub fn open(path: &Path) -> Result<Self> {
        let conn = Connection::open(path)?;
        let db = Self {
            conn: Mutex::new(conn),
        };
        db.init_tables()?;
        Ok(db)
    }

    fn init_tables(&self) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                subject TEXT NOT NULL,
                mode TEXT NOT NULL DEFAULT 'material',
                script TEXT DEFAULT '',
                keywords TEXT DEFAULT '[]',
                aspect TEXT NOT NULL DEFAULT '9:16',
                status TEXT NOT NULL DEFAULT 'draft',
                params TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );"
        )?;
        Ok(())
    }

    pub fn get_all_projects(&self) -> Result<Vec<Project>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare(
            "SELECT id, name, subject, mode, script, keywords, aspect, status, params, created_at, updated_at FROM projects ORDER BY updated_at DESC"
        )?;
        let projects = stmt.query_map([], |row| {
            Ok(Project {
                id: row.get(0)?,
                name: row.get(1)?,
                subject: row.get(2)?,
                mode: row.get(3)?,
                script: row.get(4)?,
                keywords: row.get(5)?,
                aspect: row.get(6)?,
                status: row.get(7)?,
                params: row.get(8)?,
                created_at: row.get(9)?,
                updated_at: row.get(10)?,
            })
        })?.collect::<Result<Vec<_>>>()?;
        Ok(projects)
    }

    pub fn create_project(&self, name: &str, subject: &str) -> Result<Project> {
        let conn = self.conn.lock().unwrap();
        let id = uuid::Uuid::new_v4().to_string();
        let now = chrono::Utc::now().to_rfc3339();
        conn.execute(
            "INSERT INTO projects (id, name, subject, created_at, updated_at) VALUES (?1, ?2, ?3, ?4, ?5)",
            (&id, name, subject, &now, &now),
        )?;
        Ok(Project {
            id,
            name: name.to_string(),
            subject: subject.to_string(),
            mode: "material".to_string(),
            script: String::new(),
            keywords: "[]".to_string(),
            aspect: "9:16".to_string(),
            status: "draft".to_string(),
            params: "{}".to_string(),
            created_at: now.clone(),
            updated_at: now,
        })
    }

    pub fn delete_project(&self, id: &str) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute("DELETE FROM projects WHERE id = ?1", [id])?;
        Ok(())
    }
}
