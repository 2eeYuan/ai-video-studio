use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Project {
    pub id: String,
    pub name: String,
    pub subject: String,
    pub mode: String,
    pub script: String,
    pub keywords: String,
    pub aspect: String,
    pub status: String,
    pub params: String,
    pub created_at: String,
    pub updated_at: String,
}
