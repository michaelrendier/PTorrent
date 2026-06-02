package com.ptolemy.seeder

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.LinearGradient
import android.graphics.Shader
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.view.ViewGroup.LayoutParams.MATCH_PARENT
import android.view.ViewGroup.LayoutParams.WRAP_CONTENT
import android.widget.*
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.cardview.widget.CardView
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import org.json.JSONObject
import java.io.File

// ── PGui canonical palette ────────────────────────────────────────────────────
private val C_BG       = Color.parseColor("#050d0d")
private val C_CARD     = Color.parseColor("#0d2020")
private val C_TITLEBAR = Color.parseColor("#0a1414")
private val C_RED      = Color.parseColor("#cc2200")
private val C_CYAN     = Color.parseColor("#00ffff")
private val C_BLUE     = Color.parseColor("#0055ff")
private val C_GOLD     = Color.parseColor("#c9a84c")
private val C_BTN      = Color.parseColor("#0a1a1a")
private val C_DIM      = Color.parseColor("#445555")

class MainActivity : AppCompatActivity() {

    private val progressBars  = mutableMapOf<String, ProgressBar>()
    private val statusTexts   = mutableMapOf<String, TextView>()
    private val chipTexts     = mutableMapOf<String, TextView>()
    private lateinit var cardsContainer: LinearLayout
    private lateinit var doneCard:       CardView
    private lateinit var outputText:     TextView
    private lateinit var outerLayout:    LinearLayout

    private val colorMap = mapOf(
        "gold"   to C_GOLD,
        "blue"   to C_BLUE,
        "red"    to C_RED,
        "green"  to Color.parseColor("#6EAD7A"),
        "purple" to Color.parseColor("#9B7DC8"),
        "cyan"   to C_CYAN,
        "orange" to Color.parseColor("#D4915A"),
        "silver" to Color.parseColor("#aabbbb"),
    )

    private val pickPTorrent = registerForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri: Uri? -> uri?.let { importPTorrent(it) } }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Edge-to-edge — content draws behind system bars, we handle insets
        WindowCompat.setDecorFitsSystemWindows(window, false)

        val scroll = buildLayout()
        setContentView(scroll)

        // Apply status bar inset as top padding — content never overlaps system UI
        ViewCompat.setOnApplyWindowInsetsListener(scroll) { _, insets ->
            val top = insets.getInsets(WindowInsetsCompat.Type.systemBars()).top
            outerLayout.setPadding(dp(12), top + dp(8), dp(12), dp(24))
            insets
        }

        requestNotificationPermission()
        ContextCompat.startForegroundService(this, Intent(this, SeedService::class.java))

        if (intent.action == Intent.ACTION_VIEW && intent.data != null) {
            importPTorrent(intent.data!!)
        }

        SeedLiveData.order.observe(this) { names ->
            val current = SeedLiveData.corpora.value ?: emptyMap()
            cardsContainer.removeAllViews()
            progressBars.clear(); statusTexts.clear(); chipTexts.clear()
            for (name in names) {
                val color = current[name]?.color ?: "gold"
                addCorpusCard(name, color)
            }
        }

        SeedLiveData.corpora.observe(this) { states ->
            for ((name, state) in states) {
                progressBars[name]?.apply {
                    max      = state.total.coerceAtLeast(1)
                    progress = state.idx
                }
                statusTexts[name]?.text = statusLine(state)
                chipTexts[name]?.text   = state.status
            }
        }

        SeedLiveData.allDone.observe(this) { done ->
            if (!done) return@observe
            val dir   = getExternalFilesDir(null)?.absolutePath ?: filesDir.absolutePath
            val names = SeedLiveData.order.value ?: emptyList()
            val bins  = names.joinToString("\n") { n ->
                val bin = SeedLiveData.corpora.value?.get(n)?.let {
                    binNameFromJson(n)
                } ?: "monad_${sanitize(n)}.bin"
                "  adb pull $dir/$bin"
            }
            outputText.text = "Trained bins ready:\n$dir\n\nPull to ~/.ptolemy/:\n$bins"
            doneCard.visibility = View.VISIBLE
        }
    }

    // ── layout ─────────────────────────────────────────────────────────────

    private fun buildLayout(): ScrollView {
        val scroll = ScrollView(this).apply {
            setBackgroundColor(C_BG)
            layoutParams = LinearLayout.LayoutParams(MATCH_PARENT, MATCH_PARENT)
        }

        outerLayout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            // top padding set dynamically by inset listener after layout
            setPadding(dp(12), dp(32), dp(12), dp(24))
        }

        // ── Title ──────────────────────────────────────────────────────────
        outerLayout.addView(TextView(this).apply {
            text = "Ptolemy Seeder"
            textSize = 22f
            setTextColor(C_GOLD)
            setShadowLayer(4f, 0f, 0f, Color.WHITE)
            setPadding(dp(4), 0, 0, dp(6))
            gravity = Gravity.CENTER_HORIZONTAL
        })

        // ── Gradient accent line beneath title ────────────────────────────
        outerLayout.addView(gradientStripe(height = 3), marginParams(bottom = 10))

        // ── Toolbar ───────────────────────────────────────────────────────
        outerLayout.addView(buildToolbar(), marginParams(bottom = 14))

        // ── Corpus cards ──────────────────────────────────────────────────
        cardsContainer = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        outerLayout.addView(cardsContainer)

        // ── Done card ─────────────────────────────────────────────────────
        doneCard = makeCard(C_CARD).apply { visibility = View.GONE }
        outputText = TextView(this).apply {
            setTextColor(Color.WHITE)
            setShadowLayer(3f, 0f, 0f, Color.WHITE)
            textSize = 11f
            setPadding(dp(12), dp(12), dp(12), dp(12))
            setTextIsSelectable(true)
        }
        doneCard.addView(outputText)
        outerLayout.addView(doneCard, marginParams(top = 12))

        scroll.addView(outerLayout)
        return scroll
    }

    // ── toolbar ────────────────────────────────────────────────────────────

    private fun buildToolbar(): LinearLayout {
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
        }
        // ▶ red — start J_pos flow
        row.addView(toolbarBtn("▶", C_RED) {
            startService(Intent(this, SeedService::class.java).apply {
                action = SeedService.ACTION_RESUME
            })
        })
        // ⏸ gold — Ptolemy pause
        row.addView(toolbarBtn("⏸", C_GOLD) {
            startService(Intent(this, SeedService::class.java).apply {
                action = SeedService.ACTION_PAUSE
            })
        })
        // ✕ dim — clear done
        row.addView(toolbarBtn("✕", C_DIM) {
            clearDoneCards()
        })
        // ＋ cyan — add ptorrent (critical line)
        row.addView(toolbarBtn("＋ PTorrent", C_CYAN) {
            pickPTorrent.launch("*/*")
        })
        // ⚙ white — settings
        row.addView(toolbarBtn("⚙", Color.WHITE) {
            startActivity(Intent(this, SettingsActivity::class.java))
        })
        return row
    }

    private fun toolbarBtn(label: String, color: Int, action: () -> Unit): TextView =
        TextView(this).apply {
            text  = label
            textSize = 12f
            setTextColor(color)
            setShadowLayer(3f, 0f, 0f, Color.WHITE)
            setPadding(dp(10), dp(7), dp(10), dp(7))
            setBackgroundColor(C_BTN)
            setOnClickListener { action() }
            layoutParams = LinearLayout.LayoutParams(WRAP_CONTENT, WRAP_CONTENT).also {
                it.marginEnd = dp(6)
            }
        }

    private fun clearDoneCards() {
        val order  = SeedLiveData.order.value?.toMutableList() ?: return
        val states = SeedLiveData.corpora.value ?: return
        val active = order.filter { states[it]?.status != "COMPLETE" }
        cardsContainer.removeAllViews()
        progressBars.clear(); statusTexts.clear(); chipTexts.clear()
        for (name in active) {
            val color = states[name]?.color ?: "gold"
            addCorpusCard(name, color)
        }
    }

    // ── corpus card ────────────────────────────────────────────────────────

    private fun addCorpusCard(name: String, colorKey: String) {
        val accent = colorMap[colorKey] ?: C_GOLD
        val card   = makeCard(C_CARD)

        val col = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
        }

        // Gradient stripe at top — the PGui accent line
        col.addView(gradientStripe(height = 4))

        val inner = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(12), dp(8), dp(12), dp(12))
        }

        // Name + chip row
        val nameRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        nameRow.addView(TextView(this).apply {
            text = name
            textSize = 13f
            setTextColor(Color.WHITE)
            setShadowLayer(3f, 0f, 0f, Color.WHITE)
            layoutParams = LinearLayout.LayoutParams(0, WRAP_CONTENT, 1f)
        })
        val chip = TextView(this).apply {
            text = "WAITING"
            textSize = 10f
            setTextColor(accent)
            setShadowLayer(3f, 0f, 0f, Color.WHITE)
            setPadding(dp(6), dp(2), dp(6), dp(2))
            setBackgroundColor(C_TITLEBAR)
        }
        chipTexts[name] = chip
        nameRow.addView(chip)
        inner.addView(nameRow)

        // Progress bar — gradient fill via accent color tint
        val bar = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
            max = 1; progress = 0
            progressTintList = android.content.res.ColorStateList.valueOf(accent)
            progressBackgroundTintList = android.content.res.ColorStateList.valueOf(C_TITLEBAR)
            layoutParams = LinearLayout.LayoutParams(MATCH_PARENT, dp(5)).also {
                it.topMargin = dp(6)
            }
        }
        progressBars[name] = bar
        inner.addView(bar)

        // Status line
        val statusTv = TextView(this).apply {
            text = "Waiting…"
            textSize = 10f
            setTextColor(Color.WHITE)
            setShadowLayer(2f, 0f, 0f, Color.WHITE)
            setPadding(0, dp(4), 0, 0)
        }
        statusTexts[name] = statusTv
        inner.addView(statusTv)

        col.addView(inner)
        card.addView(col)

        card.setOnClickListener {
            startActivity(
                Intent(this, CorpusDetailActivity::class.java)
                    .putExtra(CorpusDetailActivity.EXTRA_CORPUS_NAME, name)
            )
        }
        cardsContainer.addView(card, marginParams(bottom = 10))
    }

    // ── PTorrent import ────────────────────────────────────────────────────

    private fun importPTorrent(uri: Uri) {
        try {
            val text = contentResolver.openInputStream(uri)?.bufferedReader()?.readText() ?: return
            val obj  = JSONObject(text)
            val name = obj.optString("name", "unknown")
            val dir  = getExternalFilesDir(null) ?: filesDir
            val inbox = File(dir, "inbox").also { it.mkdirs() }
            File(inbox, "import_${System.currentTimeMillis()}.ptorrent").writeText(text)
            Toast.makeText(this, "PTorrent queued: $name", Toast.LENGTH_SHORT).show()
            ContextCompat.startForegroundService(this, Intent(this, SeedService::class.java))
        } catch (_: Exception) {
            Toast.makeText(this, "Could not read PTorrent file", Toast.LENGTH_SHORT).show()
        }
    }

    // ── drawing helpers ────────────────────────────────────────────────────

    // Horizontal red→cyan→blue gradient stripe matching PGui _grad
    private fun gradientStripe(height: Int): View = View(this).apply {
        background = GradientDrawable(
            GradientDrawable.Orientation.LEFT_RIGHT,
            intArrayOf(C_RED, C_CYAN, C_BLUE)
        )
        layoutParams = LinearLayout.LayoutParams(MATCH_PARENT, dp(height))
    }

    private fun makeCard(bg: Int): CardView = CardView(this).apply {
        setCardBackgroundColor(bg)
        radius        = dp(6).toFloat()
        cardElevation = dp(3).toFloat()
    }

    private fun marginParams(top: Int = 0, bottom: Int = 0) =
        LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT).also {
            it.topMargin    = dp(top)
            it.bottomMargin = dp(bottom)
        }

    private fun dp(n: Int) = (n * resources.displayMetrics.density).toInt()

    // ── status / helpers ───────────────────────────────────────────────────

    private fun statusLine(s: CorpusState): String {
        if (s.total == 0) return "Waiting…"
        val tag = if (s.tag.isNotEmpty()) "[${s.tag}]" else ""
        return "${s.idx}/${s.total}  ✓${s.studied}  ✗${s.skipped}  $tag"
    }

    private fun sanitize(name: String) =
        name.lowercase().replace(Regex("[^a-z0-9]"), "_")

    private fun binNameFromJson(name: String): String {
        val f = File(getExternalFilesDir(null) ?: filesDir, "corpus_list.json")
        if (!f.exists()) return "monad_${sanitize(name)}.bin"
        return try {
            val arr = org.json.JSONArray(f.readText())
            for (i in 0 until arr.length()) {
                val obj = arr.getJSONObject(i)
                if (obj.getString("name") == name)
                    return obj.optString("bin", "monad_${sanitize(name)}.bin")
            }
            "monad_${sanitize(name)}.bin"
        } catch (_: Exception) { "monad_${sanitize(name)}.bin" }
    }

    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
            != PackageManager.PERMISSION_GRANTED
        ) {
            ActivityCompat.requestPermissions(
                this, arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1
            )
        }
    }
}
