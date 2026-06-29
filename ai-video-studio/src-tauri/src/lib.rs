mod commands;
mod database;
mod sidecar;

use database::Database;
use sidecar::SidecarManager;
use std::sync::Arc;
use tauri::Manager;

pub struct AppState {
    pub db: Arc<Database>,
    pub sidecar: Arc<SidecarManager>,
}

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! Welcome to AI Video Studio.", name)
}

#[tauri::command]
fn get_projects(state: tauri::State<AppState>) -> Result<String, String> {
    let projects = state.db.get_all_projects().map_err(|e| e.to_string())?;
    serde_json::to_string(&projects).map_err(|e| e.to_string())
}

#[tauri::command]
fn create_project(state: tauri::State<AppState>, name: String, subject: String) -> Result<String, String> {
    let project = state.db.create_project(&name, &subject).map_err(|e| e.to_string())?;
    serde_json::to_string(&project).map_err(|e| e.to_string())
}

#[tauri::command]
fn delete_project(state: tauri::State<AppState>, id: String) -> Result<(), String> {
    state.db.delete_project(&id).map_err(|e| e.to_string())
}

#[tauri::command]
async fn start_sidecar(state: tauri::State<'_, AppState>) -> Result<(), String> {
    state.sidecar.start("python", "sidecar")
}

#[tauri::command]
fn sidecar_status(state: tauri::State<AppState>) -> bool {
    state.sidecar.is_running()
}

#[tauri::command]
async fn ai_generate_script(
    state: tauri::State<'_, AppState>,
    subject: String,
    language: String,
    paragraph_number: u8,
    custom_prompt: String,
) -> Result<String, String> {
    let resp = sidecar::generate_script(
        9527,
        &subject,
        &language,
        paragraph_number,
        &custom_prompt,
    )
    .await?;
    serde_json::to_string(&resp).map_err(|e| e.to_string())
}

#[tauri::command]
async fn ai_generate_terms(
    state: tauri::State<'_, AppState>,
    subject: String,
    script: String,
) -> Result<String, String> {
    let terms = sidecar::generate_terms(9527, &subject, &script).await?;
    serde_json::to_string(&terms).map_err(|e| e.to_string())
}

#[tauri::command]
async fn ai_start_pipeline(
    state: tauri::State<'_, AppState>,
    task_id: String,
    subject: String,
    script: String,
    keywords: String,
    shots: Option<serde_json::Value>,
) -> Result<(), String> {
    sidecar::start_pipeline(
        9527,
        &task_id,
        &subject,
        &script,
        &keywords,
        shots.as_ref(),
    )
    .await
}

#[tauri::command]
async fn ai_pipeline_status(
    state: tauri::State<'_, AppState>,
    task_id: String,
) -> Result<String, String> {
    let status = sidecar::get_pipeline_status(9527, &task_id).await?;
    serde_json::to_string(&status).map_err(|e| e.to_string())
}

#[tauri::command]
async fn export_video(
    source_path: String,
    dest_path: String,
) -> Result<(), String> {
    tokio::fs::copy(&source_path, &dest_path)
        .await
        .map_err(|e| format!("Failed to export video: {}", e))?;
    Ok(())
}

#[tauri::command]
fn get_video_url(task_id: String) -> String {
    format!("http://127.0.0.1:9527/video/{}", task_id)
}

#[tauri::command]
async fn agent_start(subject: String) -> Result<String, String> {
    let task_id = uuid::Uuid::new_v4().to_string()[..12].to_string();
    let result = sidecar::agent_start(9527, &task_id, &subject).await?;
    serde_json::to_string(&result).map_err(|e| e.to_string())
}

#[tauri::command]
async fn agent_submit_direction(task_id: String, direction_id: i32) -> Result<String, String> {
    let result = sidecar::agent_submit_direction(9527, &task_id, direction_id).await?;
    serde_json::to_string(&result).map_err(|e| e.to_string())
}

#[tauri::command]
async fn agent_submit_script(task_id: String, script: Option<serde_json::Value>) -> Result<String, String> {
    let result = sidecar::agent_submit_script(9527, &task_id, script).await?;
    serde_json::to_string(&result).map_err(|e| e.to_string())
}

#[tauri::command]
async fn agent_submit_storyboard(task_id: String) -> Result<String, String> {
    let result = sidecar::agent_submit_storyboard(9527, &task_id).await?;
    serde_json::to_string(&result).map_err(|e| e.to_string())
}

#[tauri::command]
async fn agent_status(task_id: String) -> Result<String, String> {
    let result = sidecar::agent_status(9527, &task_id).await?;
    serde_json::to_string(&result).map_err(|e| e.to_string())
}

#[tauri::command]
fn write_sidecar_config(sidecar_dir: String, settings: serde_json::Value) -> Result<(), String> {
    // Build config.yaml content from settings
    let llm = settings.get("llm").cloned().unwrap_or_default();
    let tts = settings.get("tts").cloned().unwrap_or_default();

    let api_key = llm.get("api_key").and_then(|v| v.as_str()).unwrap_or("");
    let base_url = llm.get("base_url").and_then(|v| v.as_str()).unwrap_or("https://api.openai.com/v1");
    let model = llm.get("model").and_then(|v| v.as_str()).unwrap_or("gpt-4o-mini");
    let voice = tts.get("voice").and_then(|v| v.as_str()).unwrap_or("zh-CN-YunxiNeural");

    let config = format!(
        "llm:\n  provider: \"openai\"\n  api_key: \"{api_key}\"\n  base_url: \"{base_url}\"\n  model: \"{model}\"\n\ntts:\n  provider: \"edge-tts\"\n  voice: \"{voice}\"\n  rate: 1.0\n  volume: 1.0\n\nvideo:\n  aspect: \"9:16\"\n  clip_duration: 3\n  transition: \"none\"\n  concat_mode: \"random\"\n\nsubtitle:\n  enabled: true\n  font: \"MicrosoftYaHeiBold.ttc\"\n  font_size: 60\n  font_color: \"#FFFFFF\"\n  stroke_color: \"#000000\"\n  stroke_width: 1.5\n  position: \"bottom\"\n  background: true\n  background_color: \"#000000\"\n  rounded: true\n"
    );

    let config_path = std::path::Path::new(&sidecar_dir).join("config.yaml");
    std::fs::write(&config_path, config).map_err(|e| format!("Failed to write config: {}", e))?;
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_store::Builder::default().build())
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            let app_dir = app.path().app_data_dir().expect("failed to get app data dir");
            std::fs::create_dir_all(&app_dir).expect("failed to create app data dir");
            let db_path = app_dir.join("projects.db");
            let db = Database::open(&db_path).expect("failed to open database");
            let db = Arc::new(db);
            let sidecar = Arc::new(SidecarManager::new(9527));
            app.manage(AppState { db, sidecar });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            greet,
            get_projects,
            create_project,
            delete_project,
            start_sidecar,
            sidecar_status,
            ai_generate_script,
            ai_generate_terms,
            ai_start_pipeline,
            ai_pipeline_status,
            export_video,
            get_video_url,
            write_sidecar_config,
            agent_start,
            agent_submit_direction,
            agent_submit_script,
            agent_submit_storyboard,
            agent_status,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
