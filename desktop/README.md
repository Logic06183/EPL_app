# FPL AI Pro for Mac

A small Tauri v2 app (native WebKit, ~10 MB) that opens https://epl-prediction-app.web.app
in its own window with a Dock icon. No code from `frontend/` is bundled; the app always
shows the live site.

## How sign-in works

Google blocks OAuth inside embedded webviews (`disallowed_useragent`), so:

1. The app injects `window.__FPL_DESKTOP__` before the page loads.
2. "Continue with Google" in the app navigates to `/?desktop_auth=1`; `src-tauri/src/lib.rs`
   intercepts that and opens it in the default browser instead.
3. In the browser the user signs in with Google as normal. The page then calls
   `POST /api/users/desktop-token`, which mints a Firebase custom token for that uid.
4. The browser redirects to `fplai://auth?ct=<token>`. macOS hands that URL to the app
   (scheme registered in the bundle), which calls `window.fplDesktopAuth(token)` in the
   webview, and the page finishes with `signInWithCustomToken`.

Checkout (PayFast) and any other off-site link open in the browser the same way. The
window remembers its size and position; View → Reload (⌘R) reloads the page.

Deep links only work in the bundled app, not in `tauri dev`.

## Build

```sh
cd desktop
npm install
npm run icons            # once: src-tauri/icons from ../frontend/icon.svg
npm run build            # → src-tauri/target/release/bundle/{macos,dmg}
```

Or `scripts/release-mac.sh` from the repo root, which also signs and notarises when the
`APPLE_*` variables are set. Needs Xcode command line tools and Rust (`brew install rustup`).

## Test the sign-in hand-off without Google

With the built app open:

```sh
open "fplai://auth?ct=not-a-real-token"
```

The app should come to the front and show "Sign-in failed: …" (the token is rejected by
Firebase), which proves the deep link reaches the page.
