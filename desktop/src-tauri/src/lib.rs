mod commands;
mod logs;
mod project;
mod python_bridge;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            commands::get_status,
            commands::get_queue,
            commands::run_doctor,
            commands::collect_douyin,
            commands::scan_inbox,
            commands::scan_directory,
            commands::collect_rss,
            commands::clip_webpage,
            commands::collect_platform_list,
            commands::import_links,
            commands::process_queue,
            commands::retry_item,
            commands::retry_failed,
            commands::skip_item,
            commands::knowledge_maintenance,
            commands::write_launcher,
            commands::list_recent_logs
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
