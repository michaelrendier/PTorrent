package com.ptolemy.seeder

import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.view.Gravity
import android.view.ViewGroup.LayoutParams.MATCH_PARENT
import android.view.ViewGroup.LayoutParams.WRAP_CONTENT
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.cardview.widget.CardView
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class CorpusDetailActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_CORPUS_NAME = "corpus_name"
    }

    private data class CorpusMeta(
        val name:        String,
        val color:       String,
        val description: String,
        val primaryTags: Set<String>,
        val txtFile:     String,
        val binFile:     String,
    )

    private val colorMap = mapOf(
        "gold"   to "#C9A84C",
        "blue"   to "#6EA8D4",
        "red"    to "#B05050",
        "green"  to "#6EAD7A",
        "purple" to "#9B7DC8",
        "cyan"   to "#4EC9C9",
        "orange" to "#D4915A",
    )

    private val bgColor  = Color.parseColor("#0D0D14")
    private val cardHex  = "#16161F"
    private val dimColor = Color.parseColor("#7A7A8A")

    // live-update handles
    private lateinit var statusChip:  TextView
    private val statValues = mutableMapOf<String, TextView>()   // "total" "studied" "skipped" "rate"

    // url list incremental update
    private lateinit var urlListContainer: LinearLayout
    private data class UrlRowViews(val icon: TextView, val tagView: TextView)
    private val urlRowViews = mutableListOf<UrlRowViews>()
    private var currentUrls: List<UrlState> = emptyList()

    private lateinit var meta: CorpusMeta

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val corpusName = intent.getStringExtra(EXTRA_CORPUS_NAME)
        val ptorrentUri: Uri? = if (intent.action == Intent.ACTION_VIEW) intent.data else null

        meta = loadMeta(corpusName, ptorrentUri)
        setContentView(buildLayout())

        // observe live state
        SeedLiveData.corpora.observe(this) { states ->
            states[meta.name]?.let { applyState(it) }
        }
        SeedLiveData.urlStates.observe(this) { all ->
            all[meta.name]?.let { updateUrlList(it) }
        }

        // seed initial url list from pre-populated data or txt file
        val initial = SeedLiveData.urlStates.value?.get(meta.name)
        if (initial != null && initial.isNotEmpty()) {
            updateUrlList(initial)
        } else if (meta.txtFile.isNotEmpty()) {
            val urls = parseUrlsFromFile(File(extDir(), meta.txtFile))
            if (urls.isNotEmpty()) updateUrlList(urls)
        }

        SeedLiveData.corpora.value?.get(meta.name)?.let { applyState(it) }
    }

    // ── metadata loading ───────────────────────────────────────────────────

    private fun extDir(): String = getExternalFilesDir(null)?.absolutePath
        ?: filesDir.absolutePath

    private fun loadMeta(name: String?, ptorrentUri: Uri?): CorpusMeta {
        if (name != null) {
            val f = File(extDir(), "corpus_list.json")
            if (f.exists()) {
                try {
                    val arr = JSONArray(f.readText())
                    for (i in 0 until arr.length()) {
                        val obj = arr.getJSONObject(i)
                        if (obj.getString("name") == name) return metaFrom(obj)
                    }
                } catch (_: Exception) {}
            }
        }
        if (ptorrentUri != null) {
            try {
                val text = contentResolver.openInputStream(ptorrentUri)
                    ?.bufferedReader()?.readText() ?: ""
                return metaFrom(JSONObject(text))
            } catch (_: Exception) {}
        }
        return CorpusMeta(name ?: "Unknown", "gold", "", emptySet(), "", "")
    }

    private fun metaFrom(obj: JSONObject): CorpusMeta {
        val tags = obj.optJSONArray("primary_tags")?.let { a ->
            (0 until a.length()).map { a.getString(it) }.toSet()
        } ?: emptySet()
        return CorpusMeta(
            name        = obj.getString("name"),
            color       = obj.optString("color", "gold"),
            description = obj.optString("description", ""),
            primaryTags = tags,
            txtFile     = obj.optString("txt", ""),
            binFile     = obj.optString("bin", ""),
        )
    }

    private fun parseUrlsFromFile(f: File): List<UrlState> {
        if (!f.exists()) return emptyList()
        val pat = Regex("""^\[([A-Z]+)]\s+(https?://\S+)""")
        return try {
            f.readLines()
                .filter { it.isNotBlank() && !it.startsWith("#") }
                .mapNotNull { line ->
                    pat.find(line.trim())?.let { m ->
                        UrlState(tag = m.groupValues[1], url = m.groupValues[2])
                    }
                }
        } catch (_: Exception) { emptyList() }
    }

    // ── layout ─────────────────────────────────────────────────────────────

    private fun buildLayout(): ScrollView {
        val accent = Color.parseColor(colorMap[meta.color] ?: "#C9A84C")

        val scroll = ScrollView(this).apply {
            setBackgroundColor(bgColor)
            layoutParams = LinearLayout.LayoutParams(MATCH_PARENT, MATCH_PARENT)
        }
        val outer = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(14), dp(16), dp(14), dp(32))
        }

        // back button
        outer.addView(TextView(this).apply {
            text = "← Back"
            textSize = 13f
            setTextColor(accent)
            setPadding(0, 0, 0, dp(4))
            setOnClickListener { finish() }
        }, lp(bottom = 12))

        // header card
        outer.addView(buildHeaderCard(accent), lp(bottom = 10))

        // stats card
        outer.addView(buildStatsCard(accent), lp(bottom = 10))

        // url list card
        outer.addView(buildUrlListCard(), lp(bottom = 10))

        scroll.addView(outer)
        return scroll
    }

    private fun buildHeaderCard(accent: Int): CardView {
        val card = makeCard()
        val col  = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(14), dp(12), dp(14), dp(14))
        }
        // name + status row
        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        row.addView(TextView(this).apply {
            text = meta.name; textSize = 17f; setTextColor(accent)
            layoutParams = LinearLayout.LayoutParams(0, WRAP_CONTENT, 1f)
        })
        statusChip = TextView(this).apply {
            text = "WAITING"; textSize = 10f; setTextColor(accent)
            setPadding(dp(7), dp(3), dp(7), dp(3))
            setBackgroundColor(Color.parseColor("#22222E"))
        }
        row.addView(statusChip)
        col.addView(row)

        // description
        if (meta.description.isNotEmpty()) {
            col.addView(TextView(this).apply {
                text = meta.description; textSize = 12f; setTextColor(dimColor)
                setPadding(0, dp(8), 0, 0)
            })
        }

        // primary tag chips
        if (meta.primaryTags.isNotEmpty()) {
            val chipRow = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                setPadding(0, dp(10), 0, 0)
            }
            meta.primaryTags.forEach { tag ->
                chipRow.addView(TextView(this).apply {
                    text = tag; textSize = 9f; setTextColor(accent)
                    setPadding(dp(5), dp(2), dp(5), dp(2))
                    setBackgroundColor(Color.parseColor("#22222E"))
                    layoutParams = LinearLayout.LayoutParams(WRAP_CONTENT, WRAP_CONTENT).also {
                        it.marginEnd = dp(5)
                    }
                })
            }
            col.addView(chipRow)
        }

        // bin path
        if (meta.binFile.isNotEmpty()) {
            col.addView(TextView(this).apply {
                text = "→ ${meta.binFile}"; textSize = 10f; setTextColor(dimColor)
                setPadding(0, dp(8), 0, 0)
            })
        }

        card.addView(col)
        return card
    }

    private fun buildStatsCard(accent: Int): CardView {
        val card = makeCard()
        val col  = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(4), dp(4), dp(4), dp(4))
        }
        val row1 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        val row2 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }

        addStatCell(row1, "total",   "Total URLs",   accent)
        addStatCell(row1, "studied", "Studied",      Color.parseColor("#6EAD7A"))
        addStatCell(row2, "skipped", "Skipped",      Color.parseColor("#B05050"))
        addStatCell(row2, "rate",    "Success Rate", accent)

        col.addView(row1); col.addView(row2)
        card.addView(col)
        return card
    }

    private fun addStatCell(parent: LinearLayout, key: String, label: String, color: Int) {
        val cell = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = LinearLayout.LayoutParams(0, WRAP_CONTENT, 1f)
            setPadding(dp(10), dp(10), dp(10), dp(10))
        }
        val tv = TextView(this).apply {
            text = "–"; textSize = 22f; setTextColor(color)
            gravity = Gravity.CENTER_HORIZONTAL
        }
        statValues[key] = tv
        cell.addView(tv)
        cell.addView(TextView(this).apply {
            text = label; textSize = 9f; setTextColor(dimColor)
            gravity = Gravity.CENTER_HORIZONTAL
        })
        parent.addView(cell)
    }

    private fun buildUrlListCard(): CardView {
        val card = makeCard()
        val col  = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(12), dp(10), dp(12), dp(10))
        }
        col.addView(TextView(this).apply {
            text = "URL LIST"; textSize = 10f; setTextColor(dimColor)
            letterSpacing = 0.12f
            setPadding(0, 0, 0, dp(8))
        })
        urlListContainer = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        col.addView(urlListContainer)
        card.addView(col)
        return card
    }

    // ── live update ────────────────────────────────────────────────────────

    private fun applyState(s: CorpusState) {
        statusChip.text = s.status
        statValues["total"]?.text   = if (s.total > 0) s.total.toString() else "–"
        statValues["studied"]?.text = s.studied.toString()
        statValues["skipped"]?.text = s.skipped.toString()
        statValues["rate"]?.text    = if (s.total > 0)
            "%.1f%%".format(s.studied * 100.0 / s.total) else "–"
    }

    private fun updateUrlList(urls: List<UrlState>) {
        if (urlRowViews.isEmpty() || urls.size != currentUrls.size) {
            buildUrlRows(urls)
        } else {
            // incremental — only update changed icons
            urls.forEachIndexed { i, u ->
                if (i < currentUrls.size && u.status != currentUrls[i].status) {
                    val (icon, hex) = iconFor(u.status)
                    urlRowViews[i].icon.text = icon
                    urlRowViews[i].icon.setTextColor(Color.parseColor(hex))
                }
            }
        }
        currentUrls = urls
    }

    private fun buildUrlRows(urls: List<UrlState>) {
        urlListContainer.removeAllViews()
        urlRowViews.clear()
        val isPrimary = meta.primaryTags
        urls.forEach { u ->
            val row = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                setPadding(0, dp(3), 0, dp(3))
            }
            val (icon, iconHex) = iconFor(u.status)
            val iconTv = TextView(this).apply {
                text = icon; textSize = 11f
                setTextColor(Color.parseColor(iconHex))
                layoutParams = LinearLayout.LayoutParams(dp(18), WRAP_CONTENT)
            }
            val tagColor = if (u.tag in isPrimary) "#C9A84C" else "#7A7A8A"
            val tagTv = TextView(this).apply {
                text = "[${u.tag}]"; textSize = 10f
                setTextColor(Color.parseColor(tagColor))
                layoutParams = LinearLayout.LayoutParams(dp(100), WRAP_CONTENT)
            }
            row.addView(iconTv)
            row.addView(tagTv)
            row.addView(TextView(this).apply {
                text = shortUrl(u.url); textSize = 10f
                setTextColor(dimColor)
                isSingleLine = true
                ellipsize = android.text.TextUtils.TruncateAt.END
                layoutParams = LinearLayout.LayoutParams(0, WRAP_CONTENT, 1f)
            })
            urlRowViews.add(UrlRowViews(iconTv, tagTv))
            urlListContainer.addView(row)
        }
    }

    // ── helpers ────────────────────────────────────────────────────────────

    private fun iconFor(status: String): Pair<String, String> = when (status) {
        "STUDIED" -> "✓" to "#6EAD7A"
        "SKIPPED" -> "✗" to "#B05050"
        "ACTIVE"  -> "▶" to "#C9A84C"
        else      -> "○" to "#3A3A4A"
    }

    private fun shortUrl(url: String): String {
        val s = url.removePrefix("https://").removePrefix("http://")
        return if (s.length > 55) s.take(52) + "…" else s
    }

    private fun makeCard(): CardView = CardView(this).apply {
        setCardBackgroundColor(Color.parseColor(cardHex))
        radius        = dp(8).toFloat()
        cardElevation = dp(2).toFloat()
    }

    private fun lp(top: Int = 0, bottom: Int = 0) =
        LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT).also {
            it.topMargin    = dp(top)
            it.bottomMargin = dp(bottom)
        }

    private fun dp(n: Int) = (n * resources.displayMetrics.density).toInt()
}
