# FPL AI Pro — Mobile Build Guide

## Prerequisites

| Tool | Android | iOS |
|------|---------|-----|
| Node.js ≥ 18 | ✅ | ✅ |
| Android Studio + SDK 33+ | ✅ | ❌ |
| Xcode 15+ (Mac only) | ❌ | ✅ |
| Apple Developer account ($99/yr) | ❌ | ✅ |
| Google Play account ($25 one-time) | ✅ | ❌ |

---

## 1 — Install dependencies

```bash
cd mobile
npm install
```

---

## 2 — Add platforms (first time only)

```bash
# Android
npx cap add android

# iOS (Mac only)
npx cap add ios
```

After adding Android, copy theme overrides:
```bash
cp android-overrides/res/values/colors.xml android/app/src/main/res/values/colors.xml
```

---

## 3 — Sync web assets into native projects

Run this every time you update index.html:
```bash
npx cap sync
```

---

## 4 — Build & run

### Android

Open in Android Studio and build, or run directly on a device:
```bash
npm run open:android
# Android Studio opens → Build → Generate Signed Bundle/APK
```

For a debug APK quickly:
```bash
cd android && ./gradlew assembleDebug
# Output: android/app/build/outputs/apk/debug/app-debug.apk
```

For Play Store (release AAB):
```bash
cd android && ./gradlew bundleRelease
# Output: android/app/build/outputs/bundle/release/app-release.aab
```

### iOS (Mac only)

```bash
npm run open:ios
# Xcode opens → select your team → Product → Archive → Distribute
```

---

## 5 — App icon & splash screen

Use `@capacitor/assets` to auto-generate all sizes from one image:
```bash
npm install -D @capacitor/assets
# Place a 1024×1024 icon.png and 2732×2732 splash.png in mobile/resources/
npx capacitor-assets generate
```

The icon.svg from the frontend can be exported to PNG using any tool (Figma, Inkscape, etc.).

---

## 6 — PayFast payments

PayFast redirects to `https://epl-prediction-app.web.app/?upgraded=1` after payment.
The app handles this via `allowNavigation` in capacitor.config.json — the WebView
will follow the redirect back into the app automatically.

---

## 7 — Publish

### Google Play
1. Build signed AAB (step 4)
2. Go to play.google.com/console → Create app → Upload AAB

### Apple App Store
1. Archive in Xcode (step 4)
2. Upload via Xcode Organizer → App Store Connect
3. Note: Apple may request screenshots and a demo video showing login flow
