use serde::{Deserialize, Serialize};
use std::process::{Child, Command};
use std::sync::Mutex;
#[allow(unused_imports)]
use log;

pub struct SidecarManager {
    child: Mutex<Option<Child>>,
    port: u16,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ScriptResponse {
    pub script: String,
    pub keywords: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct HealthResponse {
    pub status: String,
    pub version: String,
}

impl SidecarManager {
    pub fn new(port: u16) -> Self {
        Self {
            child: Mutex::new(None),
            port,
        }
    }

    pub fn start(&self, python_path: &str, sidecar_dir: &str) -> Result<(), String> {
        let mut child = self.child.lock().unwrap();
        if child.is_some() {
            return Ok(());
        }

        let cmd = Command::new(python_path)
            .arg("main.py")
            .current_dir(sidecar_dir)
            .env("SIDECAR_PORT", self.port.to_string())
            .env("NO_PROXY", "127.0.0.1,localhost,api.xiaomimimo.com,token-plan-cn.xiaomimimo.com,api.openai.com,api.deepseek.com")
            .env("no_proxy", "127.0.0.1,localhost,api.xiaomimimo.com,token-plan-cn.xiaomimimo.com,api.openai.com,api.deepseek.com")
            .spawn()
            .map_err(|e| format!("Failed to start sidecar: {}", e))?;

        *child = Some(cmd);
        Ok(())
    }

    pub fn stop(&self) {
        let mut child = self.child.lock().unwrap();
        if let Some(mut c) = child.take() {
            let _ = c.kill();
        }
    }

    pub fn is_running(&self) -> bool {
        let mut child = self.child.lock().unwrap();
        if let Some(c) = child.as_mut() {
            match c.try_wait() {
                Ok(Some(_)) => {
                    *child = None;
                    false
                }
                Ok(None) => true,
                Err(_) => {
                    *child = None;
                    false
                }
            }
        } else {
            false
        }
    }

    pub fn base_url(&self) -> String {
        format!("http://127.0.0.1:{}", self.port)
    }
}

pub async fn health_check(port: u16) -> Result<HealthResponse, String> {
    let url = format!("http://127.0.0.1:{}/health", port);
    let resp = reqwest::get(&url)
        .await
        .map_err(|e| format!("Health check failed: {}", e))?;
    resp.json::<HealthResponse>()
        .await
        .map_err(|e| format!("Failed to parse health response: {}", e))
}

pub async fn generate_script(
    port: u16,
    subject: &str,
    language: &str,
    paragraph_number: u8,
    custom_prompt: &str,
) -> Result<ScriptResponse, String> {
    let url = format!("http://127.0.0.1:{}/generate/script", port);
    let client = reqwest::Client::new();
    let resp = client
        .post(&url)
        .json(&serde_json::json!({
            "subject": subject,
            "language": language,
            "paragraph_number": paragraph_number,
            "custom_prompt": custom_prompt,
        }))
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;

    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        return Err(format!("Sidecar error ({}): {}", status, body));
    }

    resp.json::<ScriptResponse>()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))
}

pub async fn generate_terms(
    port: u16,
    subject: &str,
    script: &str,
) -> Result<Vec<String>, String> {
    let url = format!("http://127.0.0.1:{}/generate/terms", port);
    let client = reqwest::Client::new();
    let resp = client
        .post(&url)
        .json(&serde_json::json!({
            "subject": subject,
            "script": script,
        }))
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;

    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        return Err(format!("Sidecar error ({}): {}", status, body));
    }

    let result: serde_json::Value = resp.json()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    result["keywords"]
        .as_array()
        .map(|arr| arr.iter().filter_map(|v| v.as_str().map(String::from)).collect())
        .ok_or_else(|| "Invalid response format".to_string())
}

pub async fn start_pipeline(
    port: u16,
    task_id: &str,
    subject: &str,
    script: &str,
    keywords: &str,
    shots: Option<&serde_json::Value>,
) -> Result<(), String> {
    let url = format!("http://127.0.0.1:{}/pipeline/start", port);
    let client = reqwest::Client::new();
    let mut body = serde_json::json!({
        "task_id": task_id,
        "subject": subject,
        "script": script,
        "keywords": keywords,
    });
    if let Some(shots_val) = shots {
        body["shots"] = shots_val.clone();
    }
    let resp = client
        .post(&url)
        .json(&body)
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;

    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        return Err(format!("Sidecar error ({}): {}", status, body));
    }

    Ok(())
}

pub async fn get_pipeline_status(port: u16, task_id: &str) -> Result<serde_json::Value, String> {
    let url = format!("http://127.0.0.1:{}/pipeline/{}/status", port, task_id);
    let resp = reqwest::get(&url)
        .await
        .map_err(|e| format!("Request failed: {}", e))?;

    if !resp.status().is_success() {
        return Err(format!("Task not found: {}", task_id));
    }

    resp.json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))
}

// --- Agent API calls ---

pub async fn agent_start(port: u16, task_id: &str, subject: &str) -> Result<serde_json::Value, String> {
    let url = format!("http://127.0.0.1:{}/agent/start", port);
    let client = reqwest::Client::new();
    let resp = client
        .post(&url)
        .json(&serde_json::json!({ "task_id": task_id, "subject": subject }))
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;

    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        return Err(format!("Agent error ({}): {}", status, body));
    }

    resp.json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))
}

pub async fn agent_submit_direction(port: u16, task_id: &str, direction_id: i32) -> Result<serde_json::Value, String> {
    let url = format!("http://127.0.0.1:{}/agent/direction", port);
    let client = reqwest::Client::new();
    let resp = client
        .post(&url)
        .json(&serde_json::json!({ "task_id": task_id, "direction_id": direction_id }))
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;

    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        return Err(format!("Agent error ({}): {}", status, body));
    }

    resp.json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))
}

pub async fn agent_submit_script(port: u16, task_id: &str, script: Option<serde_json::Value>) -> Result<serde_json::Value, String> {
    let url = format!("http://127.0.0.1:{}/agent/script", port);
    let client = reqwest::Client::new();
    let resp = client
        .post(&url)
        .json(&serde_json::json!({ "task_id": task_id, "script": script }))
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;

    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        return Err(format!("Agent error ({}): {}", status, body));
    }

    resp.json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))
}

pub async fn agent_submit_storyboard(port: u16, task_id: &str) -> Result<serde_json::Value, String> {
    let url = format!("http://127.0.0.1:{}/agent/storyboard", port);
    let client = reqwest::Client::new();
    let resp = client
        .post(&url)
        .json(&serde_json::json!({ "task_id": task_id }))
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;

    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        return Err(format!("Agent error ({}): {}", status, body));
    }

    resp.json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))
}

pub async fn agent_status(port: u16, task_id: &str) -> Result<serde_json::Value, String> {
    let url = format!("http://127.0.0.1:{}/agent/{}", port, task_id);
    let resp = reqwest::get(&url)
        .await
        .map_err(|e| format!("Request failed: {}", e))?;

    if !resp.status().is_success() {
        return Err(format!("Session not found: {}", task_id));
    }

    resp.json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))
}
