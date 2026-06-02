# PTorrent Model Insertion API

Any AI model can be pointed at a PTorrent traversal via the `model_hook` field
in a `.ptorrent` file. The hook fires events during traversal and posts the
current field state + triggering text to the model endpoint.

PTorrent uses Anthropic's **Model Context Protocol (MCP)** as the standard
integration layer. MCP is model-agnostic — Claude, GPT-4, Gemini, local Ollama
instances, any MCP-compatible client can connect.

---

## Hook types

### `anthropic`

Fires the Anthropic Messages API. Requires `ANTHROPIC_API_KEY` in environment.

```json
"model_hook": {
  "type": "anthropic",
  "model": "claude-opus-4-8",
  "api_key_env": "ANTHROPIC_API_KEY",
  "system": "You are analyzing traversal data from the Ptolemy sedenion field engine. Field state and measurements are provided. Respond with semantic observations.",
  "on_event": ["checkpoint", "complete"],
  "learn_response": true,
  "response_weight": 1.5,
  "max_tokens": 512
}
```

### `openai`

OpenAI-compatible chat completion endpoint. Works with GPT-4, local Ollama,
LM Studio, any OpenAI-API-compatible server.

```json
"model_hook": {
  "type": "openai",
  "endpoint": "http://localhost:11434/v1/chat/completions",
  "model": "llama3.2",
  "api_key_env": "OPENAI_API_KEY",
  "on_event": ["page_studied"],
  "learn_response": false
}
```

### `webhook`

HTTP POST to any endpoint. Raw JSON payload. No authentication assumed.

```json
"model_hook": {
  "type": "webhook",
  "endpoint": "https://your-server.com/ptorrent-results",
  "on_event": ["checkpoint", "complete"],
  "headers": { "X-PTorrent-Secret": "your-secret" }
}
```

### `mcp`

Standard Model Context Protocol server call. Connect any MCP-compatible
client to the PTorrent MCP server.

```json
"model_hook": {
  "type": "mcp",
  "endpoint": "localhost:3001/mcp",
  "on_event": ["checkpoint"]
}
```

### `claudecode`

Injects traversal results directly into a running Claude Code session via MCP.
Closes the loop: ask Claude Code → traversal runs → results arrive in conversation.

```json
"model_hook": {
  "type": "claudecode",
  "on_event": ["checkpoint", "complete"],
  "learn_response": true,
  "response_weight": 2.0
}
```

---

## MCP server (APK)

When **Enable MCP Server** is toggled in APK Settings, the APK starts a
JSON-RPC 2.0 server on the configured port (default 3000).

**Connect from desktop via ADB:**
```bash
adb forward tcp:3001 tcp:3000
# Claude Code MCP config: localhost:3001/mcp
```

**Connect via WiFi (same network):**
```
http://PHONE_IP:3000/mcp
```

### Available MCP tools

| Tool | Parameters | Returns |
|------|-----------|---------|
| `ptorrent_list` | — | List of ptorrent files in inbox |
| `ptorrent_run` | `name: str` | `job_id: str` |
| `ptorrent_status` | `job_id: str` | Progress dict |
| `ptorrent_inject` | `job_id, url, tag, weight` | Confirmation |
| `ptorrent_abort` | `job_id: str` | Final state |
| `pull_bin` | `name: str` | Base64-encoded bin |
| `field_query` | `word: str, bin: str` | β, E, σ values |
| `field_health` | `bin: str` | BAO, Noether, vocab size |

---

## Claude Code integration

Add to `.claude/settings.json` (or global Claude Code settings):

```json
{
  "mcpServers": {
    "ptorrent": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-http-proxy",
               "http://localhost:3001/mcp"]
    }
  }
}
```

With ADB forward active (`adb forward tcp:3001 tcp:3000`), Claude Code
can now call PTorrent tools directly from conversation:

> "Run the SPARC dataset ptorrent and tell me which galaxies have
>  the highest callosum strength."

Claude Code calls `ptorrent_run("sparc_dm_scan")` → phone traverses →
`ptorrent_status()` polls → `pull_bin()` or direct result query →
measurement arrives in conversation context.

---

## Event payload

Every hook receives:

```json
{
  "event": "checkpoint",
  "ptorrent_name": "SPARC Rotation Curves",
  "job_id": "sparc_20260531_160000",
  "progress": { "studied": 47, "skipped": 3, "total": 175 },
  "field_state": {
    "bao": 0.5618,
    "noether": 0.000014,
    "vocab": 58003,
    "word_count": 1247892
  },
  "last_result": {
    "id": "NGC6503",
    "callosum": 0.8834,
    "sigma_dev": 0.0041
  }
}
```

If `learn_response: true`, the model's text response is fed through
`engine.crank.learn(response, weight=response_weight)` — grounding
the field in the model's semantic interpretation of the data.
