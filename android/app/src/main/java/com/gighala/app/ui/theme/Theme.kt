package com.gighala.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// ── Light ──────────────────────────────────────────────────────────────────
private val LightColorScheme = lightColorScheme(
    primary            = GreenPrimary,
    onPrimary          = GreenOnPrimary,
    primaryContainer   = GreenLight,
    onPrimaryContainer = GreenPrimary,
    secondary          = GoldAccent,
    onSecondary        = NeutralDark,
    secondaryContainer = GoldLight,
    background         = White,
    onBackground       = NeutralDark,
    surface            = White,
    onSurface          = NeutralDark,
    surfaceVariant     = SurfaceVariant,
    error              = ErrorRed,
    onError            = White,
    errorContainer     = ErrorRedLight
)

// ── Dark ───────────────────────────────────────────────────────────────────
private val DarkColorScheme = darkColorScheme(
    primary            = GreenLight,
    onPrimary          = GreenPrimary,
    primaryContainer   = GreenContainer,
    onPrimaryContainer = GreenOnPrimary,
    secondary          = GoldAccent,
    onSecondary        = NeutralDark,
    background         = NeutralDark,
    onBackground       = White,
    surface            = Color(0xFF1E1E1E),
    onSurface          = White
)

// ── AMOLED — pure-black for OLED displays ─────────────────────────────────
private val AmoledColorScheme = darkColorScheme(
    primary            = GreenLight,
    onPrimary          = GreenPrimary,
    primaryContainer   = GreenContainer,
    onPrimaryContainer = GreenOnPrimary,
    secondary          = GoldAccent,
    onSecondary        = NeutralDark,
    secondaryContainer = Color(0xFF3E2800),
    background         = AmoledBackground,
    onBackground       = White,
    surface            = AmoledSurface,
    onSurface          = White,
    surfaceVariant     = AmoledSurfaceVar,
    onSurfaceVariant   = NeutralLight,
    error              = ErrorRed,
    onError            = White
)

// ── Nature — warm earthy greens ────────────────────────────────────────────
private val NatureColorScheme = lightColorScheme(
    primary            = NaturePrimary,
    onPrimary          = White,
    primaryContainer   = NatureSurfaceVar,
    onPrimaryContainer = NaturePrimary,
    secondary          = NatureSecondary,
    onSecondary        = White,
    secondaryContainer = Color(0xFFEFEBE9),
    background         = NatureBackground,
    onBackground       = NeutralDark,
    surface            = White,
    onSurface          = NeutralDark,
    surfaceVariant     = NatureSurfaceVar,
    error              = ErrorRed,
    onError            = White,
    errorContainer     = ErrorRedLight
)

// ── High Contrast — maximum contrast for accessibility ────────────────────
private val HighContrastColorScheme = lightColorScheme(
    primary            = HcPrimary,
    onPrimary          = White,
    primaryContainer   = GreenLight,
    onPrimaryContainer = HcPrimary,
    secondary          = HcSecondary,
    onSecondary        = White,
    secondaryContainer = Color(0xFFFFF0C0),
    background         = HcBackground,
    onBackground       = HcOnBackground,
    surface            = HcBackground,
    onSurface          = HcOnBackground,
    surfaceVariant     = HcSurfaceVar,
    onSurfaceVariant   = HcOnBackground,
    error              = ErrorRed,
    onError            = White
)

@Composable
fun GigHalaTheme(
    themeMode: ThemeMode = ThemeMode.SYSTEM,
    content: @Composable () -> Unit
) {
    val systemDark = isSystemInDarkTheme()
    val colorScheme = when (themeMode) {
        ThemeMode.LIGHT          -> LightColorScheme
        ThemeMode.DARK           -> DarkColorScheme
        ThemeMode.SYSTEM         -> if (systemDark) DarkColorScheme else LightColorScheme
        ThemeMode.AMOLED         -> AmoledColorScheme
        ThemeMode.NATURE         -> NatureColorScheme
        ThemeMode.HIGH_CONTRAST  -> HighContrastColorScheme
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography  = GigHalaTypography,
        content     = content
    )
}
