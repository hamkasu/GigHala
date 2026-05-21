package com.gighala.app

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import com.gighala.app.services.GigHalaFirebaseService
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class GigHalaApplication : Application() {

    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                GigHalaFirebaseService.CHANNEL_ID,
                "GigHala Notifications",
                NotificationManager.IMPORTANCE_DEFAULT
            ).apply {
                description = "Alerts for messages, payments, and gig updates"
            }
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
    }
}
