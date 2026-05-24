# ============================================================
# GigHala ProGuard / R8 Rules
# ============================================================

# --------------------
# General
# --------------------
-keepattributes Signature
-keepattributes *Annotation*
-keepattributes EnclosingMethod
-keepattributes InnerClasses

# --------------------
# GigHala data models
# --------------------
# Keep all API response/request model classes (used with Moshi + Retrofit)
-keep class com.gighala.app.data.api.models.** { *; }
# Keep Room entity fields (accessed via reflection by Room runtime)
-keep class com.gighala.app.data.local.** { *; }

# --------------------
# Moshi (code-gen adapters)
# --------------------
# Moshi generates *JsonAdapter classes at compile time; keep them all
-keep class **JsonAdapter { *; }
-keep class **JsonAdapter$* { *; }
# Keep @JsonClass annotated classes and their members
-keepclassmembers @com.squareup.moshi.JsonClass class * { *; }
# Keep @Json field annotations
-keepclassmembers class * {
    @com.squareup.moshi.Json <fields>;
}
-dontwarn com.squareup.moshi.**

# --------------------
# Retrofit 2
# --------------------
-keepattributes RuntimeVisibleAnnotations
-keepattributes RuntimeVisibleParameterAnnotations
-keepclassmembers,allowshrinking,allowobfuscation interface * {
    @retrofit2.http.* <methods>;
}
-dontwarn retrofit2.**
-dontwarn javax.annotation.**
-dontwarn javax.inject.**
-keep class retrofit2.** { *; }

# --------------------
# OkHttp 3/4
# --------------------
-dontwarn okhttp3.**
-dontwarn okio.**
-keepnames class okhttp3.internal.publicsuffix.PublicSuffixDatabase

# --------------------
# Room (SQLite ORM)
# --------------------
-keep @androidx.room.Entity class * { *; }
-keep @androidx.room.Dao interface * { *; }
-keep @androidx.room.Database class * { *; }
-keepclassmembers @androidx.room.Entity class * { *; }
-keepclassmembers @androidx.room.Dao interface * { *; }
-dontwarn androidx.room.**

# --------------------
# Hilt / Dagger DI
# --------------------
-keep class dagger.hilt.** { *; }
-keep class javax.inject.** { *; }
-keep @dagger.hilt.android.HiltAndroidApp class * { *; }
-keep @dagger.hilt.InstallIn class * { *; }
-keepclassmembers class * {
    @dagger.hilt.android.lifecycle.HiltViewModel *;
    @javax.inject.Inject <init>(...);
    @javax.inject.Inject <fields>;
}
-dontwarn dagger.hilt.**
-dontwarn dagger.**

# --------------------
# Firebase / FCM
# --------------------
-keep class com.google.firebase.** { *; }
-keep class com.google.android.gms.** { *; }
-dontwarn com.google.firebase.**
-dontwarn com.google.android.gms.**
# Keep FCM service subclass
-keep class com.gighala.app.services.** { *; }

# --------------------
# Kotlin Coroutines
# --------------------
-keepclassmembernames class kotlinx.** {
    volatile <fields>;
}
-dontwarn kotlinx.coroutines.**
-keep class kotlinx.coroutines.** { *; }

# --------------------
# Kotlin Serialization / Reflection
# --------------------
-keep class kotlin.Metadata { *; }
-dontwarn kotlin.**
-keepclassmembers class ** {
    @kotlin.jvm.JvmStatic <methods>;
    @kotlin.jvm.JvmField <fields>;
}

# --------------------
# AndroidX / Jetpack Compose
# --------------------
-dontwarn androidx.**
-keep class androidx.compose.** { *; }
-keep class androidx.lifecycle.** { *; }
-keep class androidx.navigation.** { *; }
-keep class androidx.datastore.** { *; }

# --------------------
# Chrome Custom Tabs
# --------------------
-keep class androidx.browser.** { *; }

# --------------------
# Coil (image loading)
# --------------------
-dontwarn coil.**

# --------------------
# Enum classes
# --------------------
# Prevent R8 from stripping enum values accessed by name (e.g. via valueOf())
-keepclassmembers enum * {
    public static **[] values();
    public static ** valueOf(java.lang.String);
}

# --------------------
# Parcelable
# --------------------
-keepclassmembers class * implements android.os.Parcelable {
    public static final android.os.Parcelable$Creator CREATOR;
}

# --------------------
# Serializable
# --------------------
-keepclassmembers class * implements java.io.Serializable {
    private static final java.io.ObjectStreamField[] serialPersistentFields;
    private void writeObject(java.io.ObjectOutputStream);
    private void readObject(java.io.ObjectInputStream);
    java.lang.Object writeReplace();
    java.lang.Object readResolve();
}
