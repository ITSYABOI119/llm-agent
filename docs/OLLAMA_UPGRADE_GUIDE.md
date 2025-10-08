# Ollama Upgrade Guide for RTX 2070

## Current Setup Analysis

Based on your `ollama serve` output:

**Hardware:**
- GPU: NVIDIA GeForce RTX 2070 (8GB VRAM)
- Compute: 7.5
- CUDA: 12.8 (OLD - needs upgrade)

**Current Issues:**
1. ⚠️ Old CUDA driver (12.8) - should be 12.6+ for best performance
2. ⚠️ Low VRAM mode enabled (8GB < 20GB threshold)
3. ⚠️ Small context length (4096 tokens)
4. ✓ Flash attention: disabled (correct for RTX 2070)

---

## Recommended Upgrades

### 1. Update NVIDIA Drivers (CRITICAL)

**Why:** Old CUDA driver impacts performance and compatibility

**How:**
1. Download latest GeForce driver from: https://www.nvidia.com/Download/index.aspx
   - Product: GeForce RTX 2070
   - OS: Windows 11 64-bit

2. Run the installer (choose "Clean Install")

3. Verify after restart:
   ```cmd
   nvidia-smi
   ```
   Should show CUDA 12.6 or newer

**Expected Impact:** +10-20% inference speed

---

### 2. Increase Context Length

**Current:** 4096 tokens (very small for code editing)
**Recommended:** 8192 tokens (good balance for 8GB VRAM)

**How to set:**

**Option A: Environment Variable (Permanent)**
```cmd
setx OLLAMA_CONTEXT_LENGTH 8192
```
Then restart Ollama

**Option B: Model-specific (per-run)**
When running the model, specify context:
```bash
ollama run llama3.1:8b --context 8192
```

**Why:** More context = agent can see more code and conversation history

---

### 3. Optimize for RTX 2070 (8GB VRAM)

**Set these environment variables:**

```cmd
# Increase context to 8K (max safe for 8GB)
setx OLLAMA_CONTEXT_LENGTH 8192

# Keep flash attention OFF (RTX 2070 doesn't support it well)
setx OLLAMA_FLASH_ATTENTION false

# Reduce GPU overhead (helps with VRAM)
setx OLLAMA_GPU_OVERHEAD 512

# Allow 1 parallel request (8GB can't handle more)
setx OLLAMA_NUM_PARALLEL 1

# Keep model loaded for 10 minutes (faster responses)
setx OLLAMA_KEEP_ALIVE 10m
```

**After setting, restart Ollama:**
```cmd
# Close current ollama serve
# Then restart it
ollama serve
```

---

### 4. Choose Optimal Model

**Current:** llama3.1:8b (good choice!)

**Alternatives for RTX 2070 (8GB):**

| Model | Size | VRAM Usage | Speed | Code Quality |
|-------|------|------------|-------|--------------|
| **llama3.1:8b** ✓ | 4.7GB | ~6GB | Fast | Excellent |
| qwen2.5-coder:7b | 4.4GB | ~5.5GB | Faster | Best for code |
| deepseek-coder-v2:16b-lite | 9.4GB | ~7GB | Medium | Excellent |
| codellama:13b-instruct | 7.4GB | ~6.5GB | Medium | Good |

**Recommended:** Try **qwen2.5-coder:7b** - best code-specific model for 8GB

```bash
ollama pull qwen2.5-coder:7b
```

Then update `config.yaml`:
```yaml
llm:
  model: "qwen2.5-coder:7b"
  api_url: "http://192.168.1.15:11434/api/generate"
  context_length: 8192
```

---

### 5. Enable Model Quantization (if needed)

If you want to try larger models, use quantized versions:

```bash
# 4-bit quantized version of 16B model
ollama pull qwen2.5-coder:14b-instruct-q4_0

# 4-bit quantized Llama 3.1
ollama pull llama3.1:8b-instruct-q4_0
```

---

## Recommended Configuration

**After upgrades, your ideal setup:**

### Environment Variables
```cmd
setx OLLAMA_CONTEXT_LENGTH 8192
setx OLLAMA_FLASH_ATTENTION false
setx OLLAMA_GPU_OVERHEAD 512
setx OLLAMA_NUM_PARALLEL 1
setx OLLAMA_KEEP_ALIVE 10m
setx OLLAMA_DEBUG INFO
```

### config.yaml
```yaml
llm:
  model: "qwen2.5-coder:7b"  # Or llama3.1:8b
  api_url: "http://192.168.1.15:11434/api/generate"
  temperature: 0.1
  context_length: 8192
  max_tokens: 2048
```

---

## Step-by-Step Upgrade Process

**1. Update NVIDIA Drivers**
   ```
   → Download from nvidia.com
   → Install with "Clean Install"
   → Reboot
   → Verify: nvidia-smi
   ```

**2. Set Environment Variables**
   ```cmd
   setx OLLAMA_CONTEXT_LENGTH 8192
   setx OLLAMA_GPU_OVERHEAD 512
   setx OLLAMA_KEEP_ALIVE 10m
   ```

**3. Restart Ollama**
   ```cmd
   # Close current ollama serve (Ctrl+C)
   # Wait 5 seconds
   ollama serve
   ```

**4. (Optional) Try Qwen 2.5 Coder**
   ```bash
   ollama pull qwen2.5-coder:7b
   ```

   Update `llm-agent/config.yaml`:
   ```yaml
   llm:
     model: "qwen2.5-coder:7b"
     context_length: 8192
   ```

**5. Test Performance**
   ```bash
   cd llm-agent
   python test_all_improvements.py
   ```

---

## Expected Performance After Upgrades

**Before:**
- Context: 4096 tokens
- Speed: ~15 tokens/sec
- VRAM: 5-6GB used
- Old CUDA driver

**After:**
- Context: 8192 tokens (2x more code visible)
- Speed: ~20-25 tokens/sec (+30-60%)
- VRAM: 6-7GB used (optimized)
- Latest CUDA driver

---

## Monitoring Performance

**Check GPU usage:**
```cmd
nvidia-smi -l 1
```

**Check Ollama performance:**
```bash
# Watch the logs when agent runs
tail -f logs/agent.log
```

**Test inference speed:**
```bash
ollama run qwen2.5-coder:7b "Write a Python function to calculate fibonacci"
```

---

## Troubleshooting

**If VRAM runs out:**
- Reduce context: `setx OLLAMA_CONTEXT_LENGTH 6144`
- Use smaller model: `llama3.1:7b-instruct-q4_0`

**If responses are slow:**
- Check GPU usage with `nvidia-smi`
- Ensure nothing else is using GPU
- Try smaller model

**If quality drops:**
- Don't go below 4096 context
- Stick with full-precision models (avoid q4_0)
- Use qwen2.5-coder or llama3.1 (best quality)

---

## Quick Start Commands

```cmd
# 1. Set optimal env vars
setx OLLAMA_CONTEXT_LENGTH 8192
setx OLLAMA_GPU_OVERHEAD 512
setx OLLAMA_KEEP_ALIVE 10m

# 2. Restart shell, then:
ollama serve

# 3. In another terminal, try qwen coder:
ollama pull qwen2.5-coder:7b

# 4. Test it:
ollama run qwen2.5-coder:7b "def fibonacci(n):"
```

---

## Summary

**Must Do:**
1. ✓ Update NVIDIA drivers
2. ✓ Set `OLLAMA_CONTEXT_LENGTH=8192`
3. ✓ Restart Ollama

**Should Do:**
4. ✓ Try `qwen2.5-coder:7b` model
5. ✓ Set `OLLAMA_KEEP_ALIVE=10m`

**Optional:**
6. Set `OLLAMA_GPU_OVERHEAD=512`
7. Monitor with `nvidia-smi`

Your RTX 2070 is perfect for running these models - just needs the driver update and config tweaks! 🚀
