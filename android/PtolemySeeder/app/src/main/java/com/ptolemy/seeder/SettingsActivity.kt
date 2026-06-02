package com.ptolemy.seeder

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.graphics.Color
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.WindowCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.preference.Preference
import androidx.preference.PreferenceFragmentCompat
import androidx.preference.SwitchPreferenceCompat

class SettingsActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        window.statusBarColor  = Color.parseColor("#050d0d")
        window.navigationBarColor = Color.parseColor("#050d0d")

        if (savedInstanceState == null) {
            supportFragmentManager
                .beginTransaction()
                .replace(android.R.id.content, PtolSettingsFragment())
                .commit()
        }
    }

    class PtolSettingsFragment : PreferenceFragmentCompat() {

        override fun onCreatePreferences(savedInstanceState: Bundle?, rootKey: String?) {
            setPreferencesFromResource(R.xml.preferences, rootKey)

            // MCP server toggle — start/stop server
            findPreference<SwitchPreferenceCompat>("mcp_enabled")
                ?.setOnPreferenceChangeListener { _, newValue ->
                    val enable = newValue as Boolean
                    val intent = android.content.Intent(
                        requireContext(), SeedService::class.java
                    ).apply {
                        action = if (enable) SeedService.ACTION_MCP_START
                                 else        SeedService.ACTION_MCP_STOP
                    }
                    requireContext().startService(intent)
                    true
                }

            // ADB forward — tap to copy
            findPreference<Preference>("adb_forward")
                ?.setOnPreferenceClickListener {
                    val port = preferenceManager.sharedPreferences
                        ?.getString("mcp_port", "3000") ?: "3000"
                    val cmd = "adb forward tcp:3001 tcp:$port"
                    val cm  = requireContext()
                        .getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                    cm.setPrimaryClip(ClipData.newPlainText("adb forward", cmd))
                    Toast.makeText(requireContext(), "Copied: $cmd", Toast.LENGTH_SHORT).show()
                    true
                }

            // Version — show build info
            findPreference<Preference>("version")?.summary =
                "Version 3.0 (build 5) — Ptolemy Holcus Engine v1.218\n" +
                "ORCID: ${preferenceManager.sharedPreferences
                    ?.getString("orcid_id", "0009-0007-7239-6760")}"
        }
    }
}
