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
import android.text.Editable
import android.text.InputType
import android.text.TextWatcher
import org.json.JSONArray
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

        // Apply both top (status bar) and bottom (nav bar) insets so the map
        // (content) is never clipped by system chrome. Without this the last
        // ~35px of the final card is permanently hidden behind the gesture bar.
        ViewCompat.setOnApplyWindowInsetsListener(scroll) { _, insets ->
            val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            outerLayout.setPadding(dp(12), bars.top + dp(8), dp(12), bars.bottom + dp(12))
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
            // Map fills the viewport; scrollbar stays outside card content.
            isFillViewport      = true
            scrollBarStyle      = View.SCROLLBARS_OUTSIDE_INSET
            isScrollbarFadingEnabled = false
            scrollBarSize       = dp(3)
        }

        outerLayout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = android.widget.FrameLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT)
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

        // ── Create PTorrent card ───────────────────────────────────────────
        outerLayout.addView(buildCreateCard(), marginParams(top = 14))

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

    // ── Create PTorrent card ───────────────────────────────────────────────

    private fun buildCreateCard(): CardView {
        val card = makeCard(C_CARD)
        val col  = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }

        col.addView(gradientStripe(4))

        // Header — tap to expand / collapse
        val headerRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(dp(12), dp(10), dp(12), dp(10))
        }
        val arrow = TextView(this).apply {
            text     = "▶"
            textSize = 13f
            setTextColor(C_GOLD)
        }
        headerRow.addView(TextView(this).apply {
            text     = "Create PTorrent"
            textSize = 13f
            setTextColor(C_CYAN)
            setShadowLayer(3f, 0f, 0f, Color.WHITE)
            layoutParams = LinearLayout.LayoutParams(0, WRAP_CONTENT, 1f)
        })
        headerRow.addView(arrow)
        col.addView(headerRow)

        // Content — starts collapsed
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            visibility  = View.GONE
            setPadding(dp(12), dp(2), dp(12), dp(14))
        }

        // ── Type ──
        val ptorrentTypes = listOf("corpus", "evaluation", "dataset", "phonebook")
        val typeSpinner   = Spinner(this).apply {
            adapter = ArrayAdapter(
                this@MainActivity,
                android.R.layout.simple_spinner_item,
                ptorrentTypes
            ).also { it.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item) }
            setBackgroundColor(C_TITLEBAR)
        }
        content.addView(labelRow("Type",
            "corpus     — URL-list seeder; trains a .bin file\n" +
            "evaluation — in-situ σ-face query; writes .peval\n" +
            "dataset    — structured telescope / data source\n" +
            "phonebook  — reference entry only; nothing runs"))
        content.addView(typeSpinner, marginParams(bottom = 10))

        // ── Color ──
        var selectedColor = "gold"
        val colorKeys = listOf("gold", "cyan", "green", "red", "purple", "orange", "silver")
        val colorRadioGroup = RadioGroup(this).apply { orientation = RadioGroup.HORIZONTAL }
        colorKeys.forEachIndexed { i, key ->
            colorRadioGroup.addView(RadioButton(this).apply {
                id    = View.generateViewId()
                text  = key
                tag   = key
                textSize = 10f
                setTextColor(colorMap[key] ?: C_GOLD)
                buttonTintList = android.content.res.ColorStateList.valueOf(colorMap[key] ?: C_GOLD)
                setPadding(0, 0, dp(8), 0)
                if (i == 0) isChecked = true
            })
        }
        colorRadioGroup.setOnCheckedChangeListener { group, id ->
            selectedColor = group.findViewById<RadioButton>(id)?.tag as? String ?: "gold"
        }
        content.addView(labelRow("Color", "Accent color shown on the corpus card."))
        content.addView(
            HorizontalScrollView(this).apply { addView(colorRadioGroup) },
            marginParams(bottom = 10)
        )

        // ── Name ──
        val binEdit  = EditText(this).styledEdit("monad_name.bin")
        val nameEdit = EditText(this).styledEdit("Human-readable name  e.g. \"Bullet Cluster — σ-Face\"").also { ed ->
            ed.addTextChangedListener(object : TextWatcher {
                override fun beforeTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
                override fun onTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
                override fun afterTextChanged(s: Editable?) {
                    val slug = s.toString().lowercase()
                        .replace(Regex("[^a-z0-9]+"), "_").trim('_').take(32)
                    binEdit.setText("monad_$slug.bin")
                }
            })
        }
        content.addView(labelRow("Name",
            "Human-readable name. Appears on the corpus card.\n" +
            "Unicode is fine — em-dashes, σ, etc."))
        content.addView(nameEdit, marginParams(bottom = 10))

        // ── Bin ──
        content.addView(labelRow("Bin file",
            "Output .bin filename. Auto-filled from Name.\n" +
            "After seeding: adb pull …/files/monad_name.bin ~/.ptolemy/"))
        content.addView(binEdit, marginParams(bottom = 10))

        // ── Primary tags ──
        val predefined = listOf(
            "PHYSICS", "MATHEMATICS", "ENGLISH", "PYTHON", "C_POSIX",
            "FOUNDATIONS", "MEANING", "FERMAT",
            "DARK_MATTER", "BEC", "LENSING", "XRAY", "RADIO", "SZ",
            "OPTICAL", "GAMMA_NULL", "CMB", "BAO", "LAMBDA_CDM",
            "GAIA", "JWST", "EHT", "SPARC", "SETI"
        )
        val tagChecks = mutableMapOf<String, CheckBox>()
        val tagContainer = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        predefined.chunked(3).forEach { row ->
            val rowLayout = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
            row.forEach { tag ->
                val cb = CheckBox(this).apply {
                    text  = tag
                    textSize = 9f
                    setTextColor(C_DIM)
                    buttonTintList = android.content.res.ColorStateList.valueOf(C_CYAN)
                    layoutParams   = LinearLayout.LayoutParams(0, WRAP_CONTENT, 1f)
                }
                tagChecks[tag] = cb
                rowLayout.addView(cb)
            }
            // pad last row to 3 columns
            repeat(3 - row.size) {
                rowLayout.addView(View(this).apply {
                    layoutParams = LinearLayout.LayoutParams(0, WRAP_CONTENT, 1f)
                })
            }
            tagContainer.addView(rowLayout)
        }
        val customTagEdit = EditText(this).styledEdit("Custom tag — CAPS, comma-separated").also {
            it.inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_CAP_CHARACTERS
        }
        content.addView(labelRow("Primary Tags",
            "Tags that receive extra weight during seeding.\n" +
            "Tick from the list or add custom CAPS tags below."))
        content.addView(tagContainer, marginParams(bottom = 4))
        content.addView(customTagEdit, marginParams(bottom = 10))

        // ── Sources / Evaluation JSON ──
        val sourcesEdit = EditText(this).apply {
            hint      = "Paste sources[] array or evaluation{} block here  (optional for corpus)"
            setHintTextColor(C_DIM)
            setTextColor(Color.WHITE)
            setBackgroundColor(C_TITLEBAR)
            textSize  = 10f
            minLines  = 5
            gravity   = Gravity.TOP
            inputType = InputType.TYPE_CLASS_TEXT or
                        InputType.TYPE_TEXT_FLAG_MULTI_LINE or
                        InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS
            isSingleLine = false
            typeface  = android.graphics.Typeface.MONOSPACE
            setPadding(dp(8), dp(6), dp(8), dp(6))
        }
        content.addView(labelRow("Sources / Evaluation JSON",
            "Optional. Paste the \"sources\":[] array or \"evaluation\":{} block\n" +
            "from a desktop-authored .ptorrent.\n" +
            "Starts with [ → treated as sources array.\n" +
            "Starts with { → merged at top level.\n" +
            "Leave blank for a standard corpus entry."))
        content.addView(sourcesEdit, marginParams(bottom = 10))

        // ── Preview ──
        val previewText = TextView(this).apply {
            setTextColor(Color.WHITE)
            textSize  = 9f
            typeface  = android.graphics.Typeface.MONOSPACE
            setBackgroundColor(C_TITLEBAR)
            setPadding(dp(8), dp(6), dp(8), dp(6))
            setTextIsSelectable(true)
            visibility = View.GONE
        }

        fun collectAndBuild(): Pair<String, Boolean> {
            val extraTags = customTagEdit.text.toString()
                .split(",").map { it.trim().uppercase() }.filter { it.isNotEmpty() }
            val allTags = tagChecks.filter { it.value.isChecked }.keys.toList() + extraTags
            return buildPTorrent(
                type        = ptorrentTypes[typeSpinner.selectedItemPosition],
                color       = selectedColor,
                name        = nameEdit.text.toString().trim(),
                bin         = binEdit.text.toString().trim(),
                tags        = allTags,
                sourcesJson = sourcesEdit.text.toString().trim(),
            )
        }

        val validateBtn = createBtn("Validate ▶", C_CYAN, C_BTN) {
            val (json, ok) = collectAndBuild()
            previewText.text = json
            previewText.setTextColor(if (ok) Color.WHITE else C_RED)
            previewText.visibility = View.VISIBLE
        }
        val dropBtn = createBtn("Drop to Inbox  ↓", Color.BLACK, C_CYAN) {
            val (json, ok) = collectAndBuild()
            if (!ok) {
                Toast.makeText(this, "Fix errors first — tap Validate", Toast.LENGTH_SHORT).show()
                previewText.text = json
                previewText.setTextColor(C_RED)
                previewText.visibility = View.VISIBLE
                return@createBtn
            }
            dropToInbox(nameEdit.text.toString().trim(), json)
        }

        content.addView(validateBtn, marginParams(bottom = 6))
        content.addView(previewText,  marginParams(bottom = 8))
        content.addView(dropBtn,      marginParams(top = 2, bottom = 2))

        // Toggle
        headerRow.setOnClickListener {
            val expanding       = content.visibility == View.GONE
            content.visibility  = if (expanding) View.VISIBLE else View.GONE
            arrow.text          = if (expanding) "▼" else "▶"
        }

        col.addView(content)
        card.addView(col)
        return card
    }

    // ── label row with ℹ tooltip ───────────────────────────────────────────

    private fun labelRow(label: String, tooltip: String): LinearLayout =
        LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(0, dp(4), 0, dp(2))
            addView(TextView(this@MainActivity).apply {
                text     = label
                textSize = 10f
                setTextColor(C_DIM)
                layoutParams = LinearLayout.LayoutParams(WRAP_CONTENT, WRAP_CONTENT).also {
                    it.marginEnd = dp(5)
                }
            })
            addView(TextView(this@MainActivity).apply {
                text     = "ℹ"
                textSize = 11f
                setTextColor(C_GOLD)
                setOnClickListener {
                    Toast.makeText(this@MainActivity, tooltip, Toast.LENGTH_LONG).show()
                }
            })
        }

    // ── EditText style helper ──────────────────────────────────────────────

    private fun EditText.styledEdit(hintText: String): EditText = apply {
        hint     = hintText
        setHintTextColor(C_DIM)
        setTextColor(Color.WHITE)
        setBackgroundColor(C_TITLEBAR)
        textSize = 12f
        maxLines = 1
        setPadding(dp(8), dp(6), dp(8), dp(6))
    }

    // ── button helper ──────────────────────────────────────────────────────

    private fun createBtn(label: String, textColor: Int, bg: Int,
                          action: () -> Unit): TextView =
        TextView(this).apply {
            text     = label
            textSize = 12f
            setTextColor(textColor)
            setBackgroundColor(bg)
            gravity  = Gravity.CENTER
            setPadding(dp(12), dp(10), dp(12), dp(10))
            layoutParams = LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT)
            setOnClickListener { action() }
        }

    // ── ptorrent JSON builder ──────────────────────────────────────────────

    private fun buildPTorrent(
        type:        String,
        color:       String,
        name:        String,
        bin:         String,
        tags:        List<String>,
        sourcesJson: String,
    ): Pair<String, Boolean> {
        if (name.isEmpty()) return "Name is required." to false
        if (bin.isEmpty())  return "Bin filename is required." to false

        return try {
            var resolvedType = type
            val obj = JSONObject().apply {
                put("ptorrent_version", "2.0")
                put("name",  name)
                put("bin",   bin)
                put("color", color)
            }
            if (tags.isNotEmpty()) {
                val arr = JSONArray()
                tags.distinct().forEach { arr.put(it) }
                obj.put("primary_tags", arr)
            }
            if (sourcesJson.isNotEmpty()) {
                val trimmed = sourcesJson.trim()
                when {
                    trimmed.startsWith("[") -> {
                        obj.put("sources", JSONArray(trimmed))
                        if (resolvedType == "corpus") resolvedType = "evaluation"
                    }
                    trimmed.startsWith("{") -> {
                        val inner = JSONObject(trimmed)
                        inner.keys().forEach { k -> obj.put(k, inner.get(k)) }
                        if ((obj.has("sources") || obj.has("evaluation")) &&
                            resolvedType == "corpus") resolvedType = "evaluation"
                    }
                    else -> return "Sources JSON must start with [ or {" to false
                }
            }
            obj.put("type", resolvedType)
            obj.toString(2) to true
        } catch (e: Exception) {
            "JSON error: ${e.message}" to false
        }
    }

    // ── drop to inbox ──────────────────────────────────────────────────────

    private fun dropToInbox(name: String, json: String) {
        try {
            val inbox = File(getExternalFilesDir(null) ?: filesDir, "inbox").also { it.mkdirs() }
            val slug  = name.lowercase().replace(Regex("[^a-z0-9]+"), "_")
                            .trim('_').take(32)
            val file  = File(inbox, "${slug}_${System.currentTimeMillis()}.ptorrent")
            file.writeText(json)
            Toast.makeText(this, "Queued: ${file.name}", Toast.LENGTH_SHORT).show()
            ContextCompat.startForegroundService(this, Intent(this, SeedService::class.java))
        } catch (e: Exception) {
            Toast.makeText(this, "Drop failed: ${e.message}", Toast.LENGTH_SHORT).show()
        }
    }
}
