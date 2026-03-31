# Capacitor ProGuard rules
-keep class com.getcapacitor.** { *; }
-keep class com.gighala.app.** { *; }

# Firebase
-keep class com.google.firebase.** { *; }
-keep class com.google.android.gms.** { *; }

# Capacitor plugins
-keep class com.capacitorjs.** { *; }
-keep @com.getcapacitor.annotation.CapacitorPlugin public class * {*;}

# Biometric
-keep class androidx.biometric.** { *; }

# Keep JavaScript interface
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}

# Prevent stripping of native library names
-keepclasseswithmembernames class * {
    native <methods>;
}

# Keep Parcelable
-keepclassmembers class * implements android.os.Parcelable {
    public static final android.os.Parcelable$Creator CREATOR;
}

# Stripe
-keep class com.stripe.** { *; }
-dontwarn com.stripe.**
