package com.gighala.app.ui.theme

enum class ThemeMode {
    /** Force the standard light palette */
    LIGHT,
    /** Force the standard dark palette */
    DARK,
    /** Follow the device/OS setting */
    SYSTEM,
    /** Pure-black dark palette — saves battery on OLED screens */
    AMOLED,
    /** Warm earthy-green palette */
    NATURE,
    /** Maximum contrast for improved accessibility */
    HIGH_CONTRAST
}
