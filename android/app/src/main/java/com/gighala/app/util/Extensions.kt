package com.gighala.app.util

import java.text.NumberFormat
import java.util.Locale

fun Double.toMyr(): String =
    "RM ${NumberFormat.getNumberInstance(Locale("ms", "MY")).apply { maximumFractionDigits = 2; minimumFractionDigits = 2 }.format(this)}"

fun String.truncate(maxLength: Int): String =
    if (length <= maxLength) this else "${take(maxLength)}…"
