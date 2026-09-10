#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use std::process::{Child, Command};
use std::sync::Mutex;
use tauri::Manager;

// Garde le process du backend FastAPI pour pouvoir l'arrêter proprement à la fermeture de l'app.
// Avant cette modif, l'app Tauri ne lançait ni n'arrêtait ARIA : il fallait démarrer
// `python main.py` à la main à côté (voir start-dev.sh / start-production.sh), et l'app Tauri
// elle-même n'était qu'un squelette vide (juste la commande "greet" du template par défaut).
//
// Chemin du venv en dur : pensé pour ce poste de développement (ton PC), pas pour une
// distribution à d'autres machines. Pour ça il faudrait un backend packagé en exécutable
// autonome (PyInstaller) enregistré comme sidecar Tauri plutôt que d'appeler le python du venv
// directement — étape volontairement pas faite maintenant, à voir si/quand tu veux distribuer
// l'app ailleurs que sur ta machine.
struct BackendProcess(Mutex<Option<Child>>);

fn start_backend() -> Option<Child> {
    #[cfg(target_os = "windows")]
    let python = "../backend/venv/Scripts/python.exe";
    #[cfg(not(target_os = "windows"))]
    let python = "../backend/venv/bin/python";

    match Command::new(python)
        .arg("main.py")
        .current_dir("../backend")
        .spawn()
    {
        Ok(child) => {
            println!("Backend ARIA démarré (pid {})", child.id());
            Some(child)
        }
        Err(error) => {
            eprintln!(
                "Impossible de démarrer le backend ARIA ({python}) : {error}. \
                 Vérifie que backend/venv existe (voir start-dev.sh) et que le port n'est pas déjà pris."
            );
            None
        }
    }
}

fn stop_backend(app_handle: &tauri::AppHandle) {
    let state = app_handle.state::<BackendProcess>();
    // Extrait la valeur dans une instruction à part : le MutexGuard temporaire de `.lock()` doit
    // être relâché avant la fin du bloc, sinon le compilateur refuse de le laisser vivre jusqu'au
    // `if let` (erreur E0597 "does not live long enough" constatée à la compilation).
    let child = state.0.lock().unwrap().take();
    if let Some(mut child) = child {
        let _ = child.kill();
    }
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            app.manage(BackendProcess(Mutex::new(start_backend())));
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![greet])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            if let tauri::RunEvent::Exit = event {
                stop_backend(app_handle);
            }
        });
}

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}!", name)
}
