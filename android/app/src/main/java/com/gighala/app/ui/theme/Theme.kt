package com.gighala.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.*
import androidx.compose.runtime.Composable

private val LightColorScheme = lightColorScheme(
    primary          = GreenPrimary,
    onPrimary        = GreenOnPrimary,
    primaryContainer = GreenLight,
    onPrimaryContainer = GreenPrimary,
    secondary        = GoldAccent,
    onSecondary      = NeutralDark,
    secondaryContainer = GoldLight,
    background       = White,
    onBackground     = NeutralDark,
    surface          = White,
    onSurface        = NeutralDark,
    surfaceVariant   = SurfaceVariant,
    error            = ErrorRed,
    onError          = White,
    errorContainer   = ErrorRedLight
)

private val DarkColorScheme = darkColorScheme(
    primary          = GreenLight,
    onPrimary        = GreenPrimary,
    primaryContainer = GreenContainer,
    onPrimaryContainer = GreenOnPrimary,
    secondary        = GoldAccent,
    onSecondary      = NeutralDark,
    background       = NeutralDark,
    onBackground     = White,
    surface          = androidx.compose.ui.graphics.Color(0xFF1E1E1E),
    onSurface        = White
)

@Composable
fun GigHalaTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme

    MaterialTheme(
        colorScheme = colorScheme,
        typography = GigHalaTypography,
        content = content
    )
}

