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
            commands::run_doctor_json,
            commands::get_dependencies,
            commands::install_dependencies,
            commands::get_app_config,
            commands::save_app_config,
            commands::open_path,
            commands::choose_directory,
            commands::choose_backup_file,
            commands::open_url,
            commands::open_output,
            commands::backup_project,
            commands::restore_project,
            commands::export_diagnostics,
            commands::get_source_files,
            commands::save_source_files,
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
            commands::list_recent_logs,
            commands::get_accounts,
            commands::start_account_login,
            commands::confirm_account_login,
            commands::cancel_account_login,
            commands::switch_account,
            commands::verify_account,
            commands::relogin_account,
            commands::delete_account
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
