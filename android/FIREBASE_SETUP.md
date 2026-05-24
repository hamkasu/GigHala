# Firebase Setup for GigHala Android

The `google-services.json` file is **gitignored** and must be obtained from the
Firebase Console before you can build or run the app.

---

## First-time Setup

### 1. Open Firebase Console

Go to [https://console.firebase.google.com](https://console.firebase.google.com)
and sign in with the Calmic Sdn Bhd Google account.

### 2. Select (or create) the GigHala project

- Project name should be **GigHala** or **gighala-production**
- If creating fresh: choose the **Blaze** (pay-as-you-go) plan — required for
  Cloud Messaging on production

### 3. Register the Android app (if not already done)

1. In the project overview, click **Add app → Android**
2. Enter the package name exactly: **`com.gighala.app`**
3. App nickname: `GigHala Android`
4. SHA-1 (for Google Sign-In, optional for now): leave blank

### 4. Download `google-services.json`

1. After registering, Firebase will prompt you to download the file
2. Alternatively: **Project Settings → Your apps → GigHala Android →
   Download google-services.json**

### 5. Place the file

```
android/
└── app/
    └── google-services.json   ← place it here
```

Do **not** rename it. Do **not** commit it.

---

## Enable Cloud Messaging (FCM)

FCM is required for push notifications (gig alerts, payment updates, messages).

1. Firebase Console → **Build → Cloud Messaging**
2. Confirm the **Server key** is available (used by the backend to send pushes)
3. Copy the Server key into your Railway environment variable:
   ```
   FIREBASE_SERVER_KEY=AAAAxxxxxxxx...
   ```

---

## CI / CD — injecting the file in GitHub Actions

If you add a GitHub Actions workflow, inject the file from a secret:

```yaml
- name: Write google-services.json
  run: echo '${{ secrets.GOOGLE_SERVICES_JSON }}' > android/app/google-services.json
```

Store the **entire JSON contents** (minified) as the `GOOGLE_SERVICES_JSON`
repository secret.

---

## Verifying the setup

Once `google-services.json` is in place, run:

```bash
cd android
./gradlew assembleDebug
```

A successful build confirms Firebase is wired up correctly.

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `google-services.json` not found | Check the file is in `android/app/`, not `android/` |
| Package name mismatch | Confirm `package_name` in the JSON is `com.gighala.app` |
| Gradle plugin error | Ensure `google-services` plugin version matches `libs.versions.toml` (currently `4.4.2`) |
| FCM token not registering | Confirm the app is on Blaze plan and Cloud Messaging API is enabled |
