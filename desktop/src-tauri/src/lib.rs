//! FPL AI Pro for Mac: a native window around the live site.
//!
//! Sign-in gotcha: Google refuses OAuth inside embedded webviews
//! (`disallowed_useragent`), so the page never runs signInWithPopup here.
//! Instead the site opens `/?desktop_auth=1` in the system browser, signs in
//! there, asks the backend for a Firebase custom token, and redirects to
//! `fplai://auth?ct=<token>`. macOS routes that URL to this app (the scheme is
//! registered in the bundle), and we hand the token to the page, which calls
//! signInWithCustomToken. Checkout links leave the webview the same way.

use tauri::{
    menu::{Menu, MenuItemBuilder, SubmenuBuilder},
    AppHandle, Manager, WebviewUrl, WebviewWindowBuilder,
};
use tauri_plugin_deep_link::DeepLinkExt;
use tauri_plugin_opener::OpenerExt;
use tauri_plugin_window_state::{StateFlags, WindowExt};

const SITE: &str = "https://epl-prediction-app.web.app/";
const SITE_HOST: &str = "epl-prediction-app.web.app";
const WINDOW: &str = "main";

/// Pull the custom token out of `fplai://auth?ct=...` and hand it to the page.
fn deliver_auth(app: &AppHandle, urls: &[url::Url]) {
    for u in urls {
        if u.scheme() != "fplai" || u.host_str() != Some("auth") {
            continue;
        }
        let Some((_, ct)) = u.query_pairs().find(|(k, _)| k == "ct") else { continue };
        // A Firebase custom token is a JWT: base64url segments joined by dots.
        let well_formed = !ct.is_empty()
            && ct.len() < 4096
            && ct.chars().all(|c| c.is_ascii_alphanumeric() || matches!(c, '-' | '_' | '.'));
        if !well_formed {
            eprintln!("ignoring malformed fplai://auth link");
            continue;
        }
        if let Some(win) = app.get_webview_window(WINDOW) {
            let js = format!(
                "window.fplDesktopAuth ? window.fplDesktopAuth({t}) : (window.__fplPendingAuth = {t});",
                t = serde_json::to_string(&*ct).unwrap_or_default()
            );
            match win.eval(&js) {
                Ok(()) => eprintln!("fplai://auth received: token handed to the page"),
                Err(e) => eprintln!("fplai://auth received but could not reach the page: {e}"),
            }
            let _ = win.set_focus();
        }
    }
}

fn open_externally(app: &AppHandle, url: &url::Url) {
    if let Err(e) = app.opener().open_url(url.as_str(), None::<&str>) {
        eprintln!("could not open {url} in the browser: {e}");
    }
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_deep_link::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_window_state::Builder::default().build())
        .setup(|app| {
            let handle = app.handle().clone();
            let nav_handle = handle.clone();

            let win = WebviewWindowBuilder::new(app, WINDOW, WebviewUrl::External(SITE.parse()?))
                .title("FPL AI Pro")
                .inner_size(1200.0, 820.0)
                .min_inner_size(820.0, 560.0)
                // Lets the page know it is inside the Mac app (see index.html).
                .initialization_script(&format!(
                    "window.__FPL_DESKTOP__ = {{ version: '{}' }};",
                    env!("CARGO_PKG_VERSION")
                ))
                // Keep the webview on our site. Anything else (Google sign-in,
                // PayFast/Paddle checkout, calendar links) opens in the browser.
                .on_navigation(move |url| {
                    // `/?desktop_auth=1` is the browser hand-off page: it must open
                    // in the system browser, never inside this webview.
                    let handoff = url.query_pairs().any(|(k, v)| k == "desktop_auth" && v == "1");
                    let ours = !handoff
                        && (url.host_str() == Some(SITE_HOST)
                            || matches!(url.scheme(), "tauri" | "about" | "blob" | "data"));
                    if !ours {
                        open_externally(&nav_handle, url);
                    }
                    ours
                })
                .build()?;
            let _ = win.restore_state(StateFlags::all());

            // Deep links while running, and the one we may have been launched with.
            let dl_handle = handle.clone();
            app.deep_link().on_open_url(move |event| deliver_auth(&dl_handle, &event.urls()));
            if let Ok(Some(urls)) = app.deep_link().get_current() {
                deliver_auth(&handle, &urls);
            }

            // Menu: the default macOS menus plus View → Reload / Home.
            let reload = MenuItemBuilder::with_id("reload", "Reload")
                .accelerator("CmdOrCtrl+R")
                .build(app)?;
            let home = MenuItemBuilder::with_id("home", "Go to Home")
                .accelerator("CmdOrCtrl+Shift+H")
                .build(app)?;
            let view = SubmenuBuilder::new(app, "View").items(&[&reload, &home]).build()?;
            let menu = Menu::default(app.handle())?;
            menu.append(&view)?;
            app.set_menu(menu)?;
            app.on_menu_event(|app, event| {
                let Some(win) = app.get_webview_window(WINDOW) else { return };
                match event.id().0.as_str() {
                    "reload" => { let _ = win.eval("location.reload()"); }
                    "home" => { let _ = win.eval(&format!("location.href = {}", serde_json::to_string(SITE).unwrap())); }
                    _ => {}
                }
            });
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running FPL AI Pro");
}
