package com.ptolemy.seeder

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.graphics.Color
import android.os.Bundle
import android.text.InputType
import android.view.LayoutInflater
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.WindowCompat
import androidx.preference.Preference
import androidx.preference.PreferenceFragmentCompat
import androidx.preference.SwitchPreferenceCompat

class SettingsActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        window.statusBarColor   = Color.parseColor("#050d0d")
        window.navigationBarColor = Color.parseColor("#050d0d")

        if (savedInstanceState == null) {
            supportFragmentManager
                .beginTransaction()
                .replace(android.R.id.content, PtolSettingsFragment())
                .commit()
        }
    }

    // ── Settings Fragment ─────────────────────────────────────────────────────

    class PtolSettingsFragment : PreferenceFragmentCompat() {

        private val km by lazy { KeyManager.getInstance(requireContext()) }

        // Built-in slot definitions: preference key → KeyManager slot name
        private val builtInSlots = mapOf(
            "key_anthropic"  to "anthropic",
            "key_openai"     to "openai",
            "key_nist_nvd"   to "nist_nvd",
            "key_github"     to "github",
            "key_smtp_pass"  to "smtp_pass"
        )

        override fun onCreatePreferences(savedInstanceState: Bundle?, rootKey: String?) {
            setPreferencesFromResource(R.xml.preferences, rootKey)
            wireMcpToggle()
            wireAdbForward()
            wireApiKeyPreferences()
            updateVersion()
        }

        override fun onResume() {
            super.onResume()
            refreshApiKeySummaries()
        }

        // ── MCP toggle ───────────────────────────────────────────────────────

        private fun wireMcpToggle() {
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
        }

        // ── ADB forward copy ─────────────────────────────────────────────────

        private fun wireAdbForward() {
            findPreference<Preference>("adb_forward")
                ?.setOnPreferenceClickListener {
                    val port = preferenceManager.sharedPreferences
                        ?.getString("mcp_port", "3000") ?: "3000"
                    val cmd = "adb forward tcp:3001 tcp:$port"
                    val cm = requireContext()
                        .getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                    cm.setPrimaryClip(ClipData.newPlainText("adb forward", cmd))
                    Toast.makeText(requireContext(), "Copied: $cmd", Toast.LENGTH_SHORT).show()
                    true
                }
        }

        // ── Version string ───────────────────────────────────────────────────

        private fun updateVersion() {
            findPreference<Preference>("version")?.summary =
                "Version 5.0 — Ptolemy Holcus Engine v1.218\n" +
                "ORCID: ${preferenceManager.sharedPreferences
                    ?.getString("orcid_id", "0009-0007-7239-6760")}"
        }

        // ── API Keys section ─────────────────────────────────────────────────

        private fun wireApiKeyPreferences() {
            builtInSlots.forEach { (prefKey, slot) ->
                findPreference<Preference>(prefKey)?.setOnPreferenceClickListener {
                    showKeyEditDialog(slot, displayName(prefKey))
                    true
                }
            }
            findPreference<Preference>("key_add_custom")
                ?.setOnPreferenceClickListener {
                    showCustomKeyDialog()
                    true
                }
        }

        private fun refreshApiKeySummaries() {
            builtInSlots.forEach { (prefKey, slot) ->
                findPreference<Preference>(prefKey)?.summary =
                    if (km.isSet(slot)) "set  •  tap to edit or clear"
                    else                "not set"
            }
        }

        // ── Edit dialog for a built-in slot ─────────────────────────────────

        private fun showKeyEditDialog(slot: String, label: String) {
            val ctx = requireContext()
            val current = km.get(slot)

            val layout = LinearLayout(ctx).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(60, 30, 60, 10)
            }
            val input = EditText(ctx).apply {
                hint = "paste key here"
                inputType = InputType.TYPE_CLASS_TEXT or
                            InputType.TYPE_TEXT_VARIATION_PASSWORD
                setText(current ?: "")
            }
            val showToggle = CheckBox(ctx).apply {
                text = "Show"
                setOnCheckedChangeListener { _, checked ->
                    input.inputType = if (checked)
                        InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS
                    else
                        InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
                    input.setSelection(input.text.length)
                }
            }
            layout.addView(input)
            layout.addView(showToggle)

            AlertDialog.Builder(ctx)
                .setTitle(label)
                .setView(layout)
                .setPositiveButton("Save") { _, _ ->
                    val v = input.text.toString().trim()
                    if (v.isNotEmpty()) {
                        try {
                            km.set(slot, v)
                            Toast.makeText(ctx, "$label saved", Toast.LENGTH_SHORT).show()
                        } catch (e: Exception) {
                            Toast.makeText(ctx, "Error: ${e.message}", Toast.LENGTH_LONG).show()
                        }
                    }
                    refreshApiKeySummaries()
                }
                .setNeutralButton("Clear") { _, _ ->
                    try {
                        km.delete(slot)
                        Toast.makeText(ctx, "$label cleared", Toast.LENGTH_SHORT).show()
                    } catch (e: Exception) {
                        Toast.makeText(ctx, "Error: ${e.message}", Toast.LENGTH_LONG).show()
                    }
                    refreshApiKeySummaries()
                }
                .setNegativeButton("Cancel", null)
                .show()
        }

        // ── Add Custom Key dialog ────────────────────────────────────────────

        private fun showCustomKeyDialog() {
            val ctx = requireContext()
            val layout = LinearLayout(ctx).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(60, 30, 60, 10)
            }
            val labelInput = EditText(ctx).apply { hint = "label (e.g. taxii_key)" }
            val valueInput = EditText(ctx).apply {
                hint = "value"
                inputType = InputType.TYPE_CLASS_TEXT or
                            InputType.TYPE_TEXT_VARIATION_PASSWORD
            }
            val showToggle = CheckBox(ctx).apply {
                text = "Show"
                setOnCheckedChangeListener { _, checked ->
                    valueInput.inputType = if (checked)
                        InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS
                    else
                        InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
                    valueInput.setSelection(valueInput.text.length)
                }
            }
            layout.addView(labelInput)
            layout.addView(valueInput)
            layout.addView(showToggle)

            AlertDialog.Builder(ctx)
                .setTitle("Add Custom Key")
                .setView(layout)
                .setPositiveButton("Save") { _, _ ->
                    val lbl = labelInput.text.toString().trim()
                    val v   = valueInput.text.toString().trim()
                    if (lbl.isNotEmpty() && v.isNotEmpty()) {
                        try {
                            km.set(lbl, v)
                            Toast.makeText(ctx, "'$lbl' saved", Toast.LENGTH_SHORT).show()
                        } catch (e: Exception) {
                            Toast.makeText(ctx, "Error: ${e.message}", Toast.LENGTH_LONG).show()
                        }
                    } else {
                        Toast.makeText(ctx, "Label and value both required", Toast.LENGTH_SHORT).show()
                    }
                }
                .setNegativeButton("Cancel", null)
                .show()
        }

        private fun displayName(prefKey: String) = when (prefKey) {
            "key_anthropic"  -> "Anthropic API Key"
            "key_openai"     -> "OpenAI / Local API Key"
            "key_nist_nvd"   -> "NIST NVD API Key"
            "key_github"     -> "GitHub Token"
            "key_smtp_pass"  -> "SMTP Password"
            else             -> prefKey
        }
    }
}
