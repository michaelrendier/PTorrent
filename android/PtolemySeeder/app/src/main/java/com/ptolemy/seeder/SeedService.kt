package com.ptolemy.seeder

import android.app.*
import android.content.Intent
import android.os.*
import androidx.core.app.NotificationCompat
import androidx.lifecycle.LifecycleService
import androidx.lifecycle.MutableLiveData
import com.chaquo.python.PyObject
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicBoolean

data class CorpusState(
    val name:    String,
    val tag:     String = "",
    val idx:     Int    = 0,
    val total:   Int    = 0,
    val studied: Int    = 0,
    val skipped: Int    = 0,
    val status:  String = "WAITING",  // WAITING RUNNING PAUSED COMPLETE ERROR
    val color:   String = "gold",
    val error:   String = "",
)

data class UrlState(
    val tag:    String,
    val url:    String,
    val status: String = "PENDING",   // PENDING ACTIVE STUDIED SKIPPED
)

object SeedLiveData {
    val corpora   = MutableLiveData<Map<String, CorpusState>>(emptyMap())
    val urlStates = MutableLiveData<Map<String, List<UrlState>>>(emptyMap())
    val allDone   = MutableLiveData(false)
    val order     = MutableLiveData<List<String>>(emptyList())

    fun update(name: String, state: CorpusState) {
        corpora.postValue((corpora.value ?: emptyMap()) + (name to state))
    }

    fun markDone(name: String) {
        val prev = corpora.value?.get(name) ?: return
        corpora.postValue((corpora.value ?: emptyMap()) + (name to prev.copy(status = "COMPLETE")))
    }

    fun setUrlList(name: String, urls: List<UrlState>) {
        val m = urlStates.value?.toMutableMap() ?: mutableMapOf()
        m[name] = urls
        urlStates.postValue(m)
    }

    fun updateUrl(name: String, idx: Int, newStatus: String) {
        val m    = urlStates.value?.toMutableMap() ?: return
        val list = m[name]?.toMutableList() ?: return
        if (idx in list.indices) {
            list[idx] = list[idx].copy(status = newStatus)
            m[name]   = list
            urlStates.postValue(m)
        }
    }
}

class SeedService : LifecycleService() {

    companion object {
        const val CHANNEL_ID    = "ptolemy_seed"
        const val NOTIF_ID      = 1701
        const val ACTION_STOP      = "com.ptolemy.seeder.STOP"
        const val ACTION_PAUSE     = "com.ptolemy.seeder.PAUSE"
        const val ACTION_RESUME    = "com.ptolemy.seeder.RESUME"
        // MCP server actions — implementation is a stub pending Ktor integration
        const val ACTION_MCP_START = "com.ptolemy.seeder.MCP_START"
        const val ACTION_MCP_STOP  = "com.ptolemy.seeder.MCP_STOP"
    }

    private val handler      = Handler(Looper.getMainLooper())
    private val globalPaused = AtomicBoolean(false)
    private val prevStudied  = ConcurrentHashMap<String, Int>()
    private var fileObserver: FileObserver? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        super.onStartCommand(intent, flags, startId)
        when (intent?.action) {
            ACTION_STOP   -> { stopSelf(); return START_NOT_STICKY }
            ACTION_PAUSE  -> {
                globalPaused.set(true)
                updateNotification()
                // reflect pause in all RUNNING states
                val paused = (SeedLiveData.corpora.value ?: emptyMap()).mapValues { (_, s) ->
                    if (s.status == "RUNNING") s.copy(status = "PAUSED") else s
                }
                handler.post { SeedLiveData.corpora.postValue(paused) }
                return START_STICKY
            }
            ACTION_RESUME -> {
                globalPaused.set(false)
                updateNotification()
                val resumed = (SeedLiveData.corpora.value ?: emptyMap()).mapValues { (_, s) ->
                    if (s.status == "PAUSED") s.copy(status = "RUNNING") else s
                }
                handler.post { SeedLiveData.corpora.postValue(resumed) }
                return START_STICKY
            }
            ACTION_MCP_START -> {
                // TODO: start Ktor MCP server on configured port
                android.util.Log.i("PTorrent", "MCP server start requested (stub)")
                return START_STICKY
            }
            ACTION_MCP_STOP  -> {
                // TODO: stop Ktor MCP server
                android.util.Log.i("PTorrent", "MCP server stop requested (stub)")
                return START_STICKY
            }
        }
        startForeground(NOTIF_ID, buildNotification("Starting…"))
        extractAssets()
        prePopulateUrlStates()
        startInboxWatcher()
        startSeedThread()
        return START_STICKY
    }

    override fun onDestroy() {
        fileObserver?.stopWatching()
        super.onDestroy()
    }

    // ── asset extraction ───────────────────────────────────────────────────

    fun extDir(): String = getExternalFilesDir(null)?.absolutePath
        ?: filesDir.absolutePath

    private val assetFiles = listOf(
        "corpus_list.json",
        "foundations.txt",
        "meaning.txt",
        "war_corpus.txt",
        "python_corpus.txt",
        "c_corpus.txt",
        "physics_corpus.txt",
        "mathematics_corpus.txt",
        "english_corpus.txt",
    )

    // Merge bundled corpus_list.json into the existing file.
    // New entries in the bundled version are added; user-added entries (via ptorrent) are preserved.
    private fun mergeCorpusJson(dir: String) {
        val dest = File(dir, "corpus_list.json")
        val bundledText = try {
            assets.open("corpus_list.json").bufferedReader().readText()
        } catch (_: Exception) { return }

        if (!dest.exists()) {
            dest.writeText(bundledText)
            return
        }

        val existing = try { JSONArray(dest.readText()) } catch (_: Exception) { JSONArray() }
        val bundled  = try { JSONArray(bundledText) } catch (_: Exception) { return }

        val existingNames = (0 until existing.length())
            .map { existing.getJSONObject(it).optString("name") }
            .toSet()

        var changed = false
        for (i in 0 until bundled.length()) {
            val entry = bundled.getJSONObject(i)
            val name  = entry.optString("name")
            if (name.isNotEmpty() && name !in existingNames) {
                existing.put(entry)
                changed = true
            }
        }
        if (changed) dest.writeText(existing.toString(2))
    }

    private fun extractAssets() {
        val dir = extDir()
        mergeCorpusJson(dir)
        for (name in assetFiles) {
            if (name == "corpus_list.json") continue
            val dest = File(dir, name)
            if (!dest.exists()) {
                try {
                    assets.open(name).use { inp ->
                        dest.outputStream().use { out -> inp.copyTo(out) }
                    }
                } catch (_: Exception) {}
            }
        }
    }

    // ── url list pre-population ────────────────────────────────────────────

    private fun prePopulateUrlStates() {
        for ((name, _, txt) in loadCorpusOrder()) {
            if (txt.isEmpty()) continue
            val urls = parseUrlList(File(extDir(), txt))
            if (urls.isNotEmpty()) handler.post { SeedLiveData.setUrlList(name, urls) }
        }
    }

    fun parseUrlList(f: File): List<UrlState> {
        if (!f.exists()) return emptyList()
        val pattern = Regex("""^\[([A-Z]+)]\s+(https?://\S+)""")
        return try {
            f.readLines()
                .filter { it.isNotBlank() && !it.startsWith("#") }
                .mapNotNull { line ->
                    pattern.find(line.trim())?.let { m ->
                        UrlState(tag = m.groupValues[1], url = m.groupValues[2])
                    }
                }
        } catch (_: Exception) { emptyList() }
    }

    // ── inbox FileObserver ─────────────────────────────────────────────────

    private fun startInboxWatcher() {
        val inbox  = File(extDir(), "inbox").also { it.mkdirs() }
        val events = FileObserver.CLOSE_WRITE or FileObserver.MOVED_TO
        fileObserver = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            object : FileObserver(inbox, events) {
                override fun onEvent(event: Int, path: String?) = handleInboxFile(path)
            }
        } else {
            @Suppress("DEPRECATION")
            object : FileObserver(inbox.absolutePath, events) {
                override fun onEvent(event: Int, path: String?) = handleInboxFile(path)
            }
        }
        fileObserver?.startWatching()
    }

    private fun handleInboxFile(filename: String?) {
        if (filename?.endsWith(".ptorrent") != true) return
        val file = File(File(extDir(), "inbox"), filename)
        try {
            val obj      = JSONObject(file.readText())
            val listFile = File(extDir(), "corpus_list.json")
            val arr      = JSONArray(listFile.readText())
            val newName  = obj.optString("name", "")
            // deduplicate
            var exists = false
            for (i in 0 until arr.length()) {
                if (arr.getJSONObject(i).optString("name") == newName) { exists = true; break }
            }
            if (!exists && newName.isNotEmpty()) {
                arr.put(obj)
                listFile.writeText(arr.toString(2))
                // pre-populate url list from embedded urls array
                val urls = obj.optJSONArray("urls")?.let { a ->
                    (0 until a.length()).mapNotNull { i ->
                        val u = a.getJSONObject(i)
                        UrlState(
                            tag = u.optString("tag", ""),
                            url = u.optString("url", "")
                        ).takeIf { it.url.isNotEmpty() }
                    }
                } ?: emptyList()
                if (urls.isNotEmpty()) handler.post { SeedLiveData.setUrlList(newName, urls) }
            }
            file.delete()
        } catch (_: Exception) {}
    }

    // ── corpus manifest ────────────────────────────────────────────────────

    data class CorpusMeta(val name: String, val color: String, val txt: String)

    fun loadCorpusOrder(): List<CorpusMeta> {
        val f = File(extDir(), "corpus_list.json")
        if (!f.exists()) return emptyList()
        return try {
            val arr = JSONArray(f.readText())
            (0 until arr.length()).map { i ->
                val obj = arr.getJSONObject(i)
                CorpusMeta(
                    name  = obj.getString("name"),
                    color = obj.optString("color", "gold"),
                    txt   = obj.optString("txt", ""),
                )
            }
        } catch (_: Exception) { emptyList() }
    }

    // ── Python seed thread ─────────────────────────────────────────────────

    private fun startSeedThread() {
        val meta = loadCorpusOrder()
        handler.post {
            SeedLiveData.order.value = meta.map { it.name }
            SeedLiveData.corpora.value = meta.associate { m ->
                m.name to CorpusState(name = m.name, color = m.color)
            }
        }

        Thread {
            if (!Python.isStarted()) Python.start(AndroidPlatform(this))
            val py     = Python.getInstance()
            val runner = py.getModule("seed_runner")
            val extDir = extDir()

            val callback = PyObject.fromJava(object : Any() {
                @Suppress("unused")
                fun __call__(
                    name: String, tag: String,
                    @Suppress("UNUSED_PARAMETER") url: String,
                    idx: Int, total: Int, studied: Int, skipped: Int
                ) {
                    // blocks Python thread when paused — resumes at next URL boundary
                    while (globalPaused.get()) Thread.sleep(200)

                    val color = meta.find { it.name == name }?.color ?: "gold"
                    val state = CorpusState(
                        name = name, tag = tag,
                        idx = idx + 1, total = total,
                        studied = studied, skipped = skipped,
                        status = "RUNNING", color = color,
                    )
                    val prevS     = prevStudied[name] ?: 0
                    val urlStatus = if (studied > prevS) "STUDIED" else "SKIPPED"
                    prevStudied[name] = studied

                    handler.post {
                        SeedLiveData.update(name, state)
                        SeedLiveData.updateUrl(name, idx, urlStatus)
                        if (idx + 1 < total) SeedLiveData.updateUrl(name, idx + 1, "ACTIVE")
                        updateNotification()
                    }
                }
            })

            try {
                runner.callAttr("run_all", extDir, callback, 15)
                handler.post {
                    (SeedLiveData.order.value ?: emptyList()).forEach { SeedLiveData.markDone(it) }
                    SeedLiveData.allDone.value = true
                    updateNotification(done = true)
                }
            } catch (e: Exception) {
                handler.post { updateNotification(error = e.message ?: "error") }
            }
        }.also { it.isDaemon = true; it.name = "PtolemySeed" }.start()
    }

    // ── notifications ──────────────────────────────────────────────────────

    private fun createNotificationChannel() {
        val ch = NotificationChannel(
            CHANNEL_ID, "Ptolemy Seeder", NotificationManager.IMPORTANCE_LOW
        ).apply { description = "Corpus seeding" }
        getSystemService(NotificationManager::class.java).createNotificationChannel(ch)
    }

    private fun buildNotification(text: String, done: Boolean = false): Notification {
        val mainPi = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE
        )
        val togglePi = if (globalPaused.get()) {
            PendingIntent.getService(
                this, 1,
                Intent(this, SeedService::class.java).apply { action = ACTION_RESUME },
                PendingIntent.FLAG_IMMUTABLE
            )
        } else {
            PendingIntent.getService(
                this, 2,
                Intent(this, SeedService::class.java).apply { action = ACTION_PAUSE },
                PendingIntent.FLAG_IMMUTABLE
            )
        }
        val toggleLabel = if (globalPaused.get()) "▶ Resume" else "⏸ Pause"
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(
                when {
                    done               -> "Ptolemy Seeder — Complete"
                    globalPaused.get() -> "Ptolemy Seeder — Paused"
                    else               -> "Ptolemy Seeder"
                }
            )
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentIntent(mainPi)
            .addAction(0, toggleLabel, togglePi)
            .setOngoing(!done)
            .setSilent(true)
            .build()
    }

    private fun updateNotification(done: Boolean = false, error: String = "") {
        val states = SeedLiveData.corpora.value ?: emptyMap()
        val text = when {
            error.isNotEmpty()     -> "Error: $error"
            done                   -> "All complete — pull .bin files to ~/.ptolemy/"
            globalPaused.get()     -> "Paused"
            else -> states.values
                .filter { it.status == "RUNNING" }
                .joinToString("  ") { "${it.name.take(4)}:${it.idx}/${it.total}" }
                .ifEmpty { "Running…" }
        }
        getSystemService(NotificationManager::class.java)
            .notify(NOTIF_ID, buildNotification(text, done))
    }
}
