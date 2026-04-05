package com.gighala.app.di

import android.content.Context
import androidx.room.Room
import com.gighala.app.BuildConfig
import com.gighala.app.data.api.ApiService
import com.gighala.app.data.local.AppDatabase
import com.gighala.app.util.CsrfInterceptor
import com.gighala.app.util.PersistentCookieJar
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import java.util.concurrent.TimeUnit
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides
    @Singleton
    fun provideCookieJar(): PersistentCookieJar = PersistentCookieJar()

    @Provides
    @Singleton
    fun provideCsrfInterceptor(): CsrfInterceptor = CsrfInterceptor()

    @Provides
    @Singleton
    fun provideOkHttpClient(
        cookieJar: PersistentCookieJar,
        csrfInterceptor: CsrfInterceptor
    ): OkHttpClient {
        val logging = HttpLoggingInterceptor().apply {
            level = if (BuildConfig.DEBUG) HttpLoggingInterceptor.Level.BODY
                    else HttpLoggingInterceptor.Level.NONE
        }
        return OkHttpClient.Builder()
            .cookieJar(cookieJar)
            .addInterceptor { chain ->
                val request = chain.request().newBuilder()
                    .header("X-Requested-With", "XMLHttpRequest")
                    .header("Referer", BuildConfig.BASE_URL + "/")
                    .header("Origin", BuildConfig.BASE_URL)
                    .build()
                chain.proceed(request)
            }
            .addInterceptor(csrfInterceptor)
            .addInterceptor(logging)
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .build()
    }

    @Provides
    @Singleton
    fun provideMoshi(): Moshi = Moshi.Builder()
        .addLast(KotlinJsonAdapterFactory())
        .build()

    @Provides
    @Singleton
    fun provideRetrofit(okHttpClient: OkHttpClient, moshi: Moshi): Retrofit =
        Retrofit.Builder()
            .baseUrl(BuildConfig.BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(MoshiConverterFactory.create(moshi))
            .build()

    @Provides
    @Singleton
    fun provideApiService(retrofit: Retrofit): ApiService =
        retrofit.create(ApiService::class.java)

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): AppDatabase =
        Room.databaseBuilder(context, AppDatabase::class.java, "gighala.db")
            .fallbackToDestructiveMigration()
            .build()

    @Provides
    fun provideGigDao(db: AppDatabase) = db.gigDao()
}
