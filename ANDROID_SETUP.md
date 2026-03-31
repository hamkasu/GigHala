# GigHala Android App Setup Guide

## Architecture

```
GigHala Web (Flask)  ←──── Capacitor WebView ────→  Android Shell
      ↑                                                    ↑
  /api/mobile/*                               Native plugins:
  X-Mobile-App: true                          • Push Notifications (FCM)
                                              • Camera / Gallery
                                              • Biometric Auth
                                              • Haptics, Network, etc.
```

The app renders your existing Flask web pages inside a Capacitor WebView, adding native Android capabilities via the JS bridge in `static/js/capacitor-init.js`.

---

## Prerequisites

| Tool | Version |
|------|---------|
| Node.js | ≥ 18 |
| Android Studio | Hedgehog (2023.1.1) or newer |
| Android SDK | API 34 (target) / API 23 (min) |
| JDK | 17 |

---

## Initial Setup

### 1. Install Node dependencies
```bash
npm install
```

### 2. Set your server URL
Edit `capacitor.config.ts` and update the `server.url` to your Railway/production URL:
```ts
server: {
  url: 'https://YOUR-APP.up.railway.app',
}
```
For **local development**, change to:
```ts
server: {
  url: 'http://10.0.2.2:5000',   // Android emulator → host machine
  cleartext: true,
}
```

### 3. Add the Android platform (first time only)
```bash
npx cap add android
```

### 4. Sync web assets & plugins
```bash
npx cap sync android
```
Run this every time you change `capacitor.config.ts` or install new plugins.

### 5. Open in Android Studio
```bash
npx cap open android
```

---

## Firebase (Push Notifications)

1. Go to [Firebase Console](https://console.firebase.google.com/) → Add project → "GigHala"
2. Register Android app with package name `com.gighala.app`
3. Download `google-services.json` and place it at `android/app/google-services.json`
4. In Railway env vars, add:
   - `FCM_SERVER_KEY` — your Firebase server key (for server-side push sending)

The app will automatically register the FCM token and send it to `/api/mobile/register-push-token` on first launch.

---

## Biometric Login Flow

1. User logs in with email/password on first app launch
2. App calls `POST /api/mobile/enable-biometric` to store their user ID in the server session
3. On subsequent launches, the biometric button appears on the login screen
4. Tapping it triggers the device fingerprint/face prompt via `GigHalaBiometric.authenticate()`
5. On success, the app calls `POST /api/mobile/biometric-login` to complete the session

---

## Camera / Photo Upload

Any `<input type="file">` can be upgraded to use the native camera by adding:
```html
<!-- data-native-camera="#targetInput" triggers native camera on tap -->
<button data-native-camera="#profile-photo-input" data-preview="#preview-img">
    Ambil Foto
</button>
<input type="file" id="profile-photo-input" accept="image/*" hidden>
<img id="preview-img" src="" alt="Preview">
```

The JS bridge intercepts the button click, opens the native camera/gallery, and injects the selected file back into the hidden input automatically.

---

## Building a Release APK / AAB

### 1. Generate a signing keystore (one time)
```bash
keytool -genkey -v \
  -keystore android/release.keystore \
  -alias gighala \
  -keyalg RSA -keysize 2048 \
  -validity 10000
```

### 2. Build
```bash
# In Android Studio: Build → Generate Signed Bundle/APK
# Or via Gradle:
cd android
./gradlew bundleRelease   # AAB for Play Store
./gradlew assembleRelease # APK for sideloading
```

Output: `android/app/build/outputs/bundle/release/app-release.aab`

---

## Flask Mobile API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/mobile/register-push-token` | Save FCM token for user |
| `POST` | `/api/mobile/biometric-login` | Complete biometric session |
| `POST` | `/api/mobile/enable-biometric` | Enable biometric for next login |
| `POST` | `/api/mobile/upload-photo` | Upload camera photo |
| `GET`  | `/api/mobile/gigs` | Lightweight gig listing |
| `GET`  | `/api/mobile/profile` | Current user profile |
| `GET`  | `/api/mobile/notifications` | Unread notifications |
| `POST` | `/api/mobile/notifications/<id>/read` | Mark notification read |
| `GET`  | `/api/mobile/config` | App runtime config |

All mobile endpoints require the `X-Mobile-App: true` header.

---

## Using the Mobile Base Template

For pages that should use the mobile-optimised layout (bottom nav, safe areas):
```html
{% extends 'mobile_base.html' %}

{% block title %}Gig Saya{% endblock %}

{% block content %}
  <!-- your page content -->
{% endblock %}
```

---

## Adding Biometric Button to Login Page

Add this include anywhere inside your login form:
```html
{% include 'mobile_login_snippet.html' %}
```

---

## Environment Variables (New)

| Variable | Description |
|----------|-------------|
| `FCM_SERVER_KEY` | Firebase Cloud Messaging server key |
| `CAPACITOR_SERVER_URL` | Override server URL at build time |
| `KEYSTORE_PASSWORD` | Android release keystore password |
| `KEYSTORE_ALIAS_PASSWORD` | Android key alias password |

---

## File Structure Added

```
GigHala/
├── package.json                          # Node deps (Capacitor + plugins)
├── capacitor.config.ts                   # Capacitor configuration
├── mobile_api.py                         # Flask mobile Blueprint
├── ANDROID_SETUP.md                      # This file
├── static/
│   ├── js/capacitor-init.js              # Native plugin JS bridge
│   └── css/mobile.css                    # Mobile-specific styles
├── templates/
│   ├── mobile_base.html                  # Mobile-optimised base template
│   └── mobile_login_snippet.html        # Biometric login button
└── android/
    ├── build.gradle                      # Root Gradle config
    ├── settings.gradle                   # Module & plugin includes
    ├── gradle.properties                 # JVM/Gradle settings
    ├── gradle/wrapper/
    │   └── gradle-wrapper.properties    # Gradle version
    └── app/
        ├── build.gradle                  # App-level Gradle config
        ├── proguard-rules.pro            # R8 keep rules
        └── src/main/
            ├── AndroidManifest.xml       # Permissions & activities
            ├── java/com/gighala/app/
            │   ├── MainActivity.java     # Entry point
            │   └── plugins/
            │       └── BiometricPlugin.java
            └── res/
                ├── values/colors.xml, strings.xml, styles.xml
                ├── values-night/styles.xml
                ├── xml/network_security_config.xml
                ├── xml/file_paths.xml
                └── drawable/ic_stat_gighala.xml
```
