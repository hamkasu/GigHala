package com.gighala.app.data.local

import androidx.room.*
import com.gighala.app.data.api.models.CachedGig
import kotlinx.coroutines.flow.Flow

@Dao
interface GigDao {

    @Query("SELECT * FROM cached_gigs ORDER BY cachedAt DESC")
    fun observeAll(): Flow<List<CachedGig>>

    @Query("SELECT * FROM cached_gigs WHERE id = :id")
    suspend fun getById(id: Int): CachedGig?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(gigs: List<CachedGig>)

    @Query("DELETE FROM cached_gigs WHERE cachedAt < :before")
    suspend fun evictOlderThan(before: Long)

    @Query("DELETE FROM cached_gigs")
    suspend fun clearAll()
}
