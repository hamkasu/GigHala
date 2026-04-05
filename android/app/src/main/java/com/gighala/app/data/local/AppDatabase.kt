package com.gighala.app.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import com.gighala.app.data.api.models.CachedGig

@Database(
    entities = [CachedGig::class],
    version = 1,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun gigDao(): GigDao
}
