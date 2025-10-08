# Ollama Serve Requirement

## Do You Need to Run `ollama serve`?

**YES** - The agent requires Ollama server to be running in a separate terminal.

---

## Why Is This Required?

The LLM agent communicates with local language models (OpenThinker, Qwen, DeepSeek) through Ollama's API server. Without `ollama serve` running, the agent cannot access any models.

**Think of it like this:**
- **Ollama** = Database server (stores and runs models)
- **Agent** = Application (sends requests to the database)

Just like you need MySQL running to use a database application, you need Ollama running to use LLM models.

---

## How to Start Ollama Server

### Option 1: Separate Terminal (Recommended)

**Windows:**
```cmd
# Open a new Command Prompt window
ollama serve
```

**Keep this terminal open** while using the agent. You'll see logs like:
```
Ollama running on http://localhost:11434
Loaded model: qwen2.5-coder:7b
```

### Option 2: Background Service (Advanced)

**Windows (using Task Scheduler):**
1. Create scheduled task to run `ollama serve` at startup
2. Set to run in background

**Linux/Mac:**
```bash
# Run as systemd service or use screen/tmux
screen -dmS ollama ollama serve
```

---

## How to Verify Ollama Is Running

### Method 1: Check with curl
```bash
curl http://localhost:11434/api/tags
```

**Expected output:**
```json
{
  "models": [
    {"name": "openthinker3-7b", ...},
    {"name": "qwen2.5-coder:7b", ...}
  ]
}
```

### Method 2: Check with browser
Open: http://localhost:11434

**Expected:** "Ollama is running"

### Method 3: Check from agent
The agent will log an error if Ollama is not reachable:
```
ERROR: Could not connect to Ollama at http://localhost:11434
```

---

## Configuration

The agent connects to Ollama using settings in [config.yaml](../config.yaml):

```yaml
ollama:
  host: "localhost"
  port: 11434
  model: "qwen2.5-coder:7b"
```

**If you changed Ollama's port**, update `config.yaml` to match.

---

## Common Issues

### Issue 1: "Connection refused" error

**Cause:** Ollama server is not running

**Solution:**
```cmd
# Open new terminal
ollama serve
```

---

### Issue 2: "Model not found" error

**Cause:** Model not downloaded yet

**Solution:**
```bash
# Download required models
ollama pull openthinker3-7b
ollama pull qwen2.5-coder:7b
```

Verify with:
```bash
ollama list
```

---

### Issue 3: Ollama running but agent can't connect

**Cause:** Firewall or incorrect host/port

**Solution:**
1. Check if Ollama is listening:
   ```bash
   netstat -an | findstr 11434
   ```

2. Verify config.yaml has correct host/port:
   ```yaml
   ollama:
     host: "localhost"  # Try "127.0.0.1" if localhost fails
     port: 11434
   ```

3. Check Windows Firewall allows localhost connections

---

### Issue 4: Ollama serve crashes or exits

**Cause:** Insufficient VRAM or RAM

**Solution:**
1. Close other applications using GPU
2. Check GPU memory:
   ```cmd
   nvidia-smi
   ```

3. If VRAM is full, reduce model size:
   ```bash
   # Use smaller quantized models
   ollama pull qwen2.5-coder:7b-q4_0
   ```

---

## Performance Tips

### Keep Models Preloaded in RAM

The agent uses `keep_alive` to keep models in RAM for fast swaps:

```yaml
ollama:
  keep_alive: "60m"  # Keep models in RAM for 1 hour
```

**What this does:**
- **Without keep_alive:** Model loads from disk every time (5-8 seconds)
- **With keep_alive:** Model already in RAM (500ms swap time)

**Result:** 10-20x faster model switching!

### Verify Preloading Works

After starting the agent, check Ollama logs:
```
[INFO] Preloaded openthinker3-7b to RAM (6.2s)
[INFO] Preloaded qwen2.5-coder:7b to RAM (5.8s)
```

Models will stay in RAM for 60 minutes of inactivity.

---

## Workflow Summary

**Every time you use the agent:**

1. **Open Terminal 1:**
   ```cmd
   ollama serve
   ```
   Keep this running.

2. **Open Terminal 2:**
   ```cmd
   cd llm-agent
   python agent.py
   ```
   Or run tests:
   ```cmd
   python test_cursor_improvements.py
   ```

3. **When done:**
   - Close Terminal 2 (agent)
   - `Ctrl+C` in Terminal 1 (ollama serve)

---

## Troubleshooting Commands

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# List downloaded models
ollama list

# Download missing models
ollama pull openthinker3-7b
ollama pull qwen2.5-coder:7b

# Check GPU usage
nvidia-smi

# Check Ollama version
ollama --version

# Restart Ollama (if hanging)
# Windows: Ctrl+C in ollama serve terminal, then restart
# Linux/Mac: pkill ollama && ollama serve
```

---

## Alternative: Use Remote Ollama

If you have Ollama running on another machine:

**config.yaml:**
```yaml
ollama:
  host: "192.168.1.100"  # IP of machine running Ollama
  port: 11434
```

**On the Ollama machine:**
```bash
# Allow external connections
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

---

## Summary

| Question | Answer |
|----------|--------|
| Do I need to run ollama serve? | **YES** - Required for agent to work |
| Can I close it? | **NO** - Keep it running while using agent |
| Which terminal? | **Separate terminal** - keeps logs visible |
| How to verify? | `curl http://localhost:11434/api/tags` |
| When to restart? | If you see "connection refused" errors |

---

For more information:
- [Ollama Documentation](https://ollama.com/docs)
- [Model Configuration](../config.yaml)
- [Ollama Upgrade Guide](OLLAMA_UPGRADE_GUIDE.md)
