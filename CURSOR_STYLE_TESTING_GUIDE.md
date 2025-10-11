# Cursor-Style Architecture Testing Guide
## RTX 2070 8GB VRAM Optimization

**Date:** 2025-10-12
**Purpose:** Verify Cursor-style implementation and VRAM optimization
**Hardware:** RTX 2070 8GB VRAM, 32GB RAM, 2700x CPU

---

## Pre-Testing Checklist

### 1. Verify Ollama Models
```bash
ollama list
```

**Required models:**
- ✅ openthinker3-7b (4.7GB) - Orchestrator
- ✅ phi3:mini (2.2GB) - Tool formatter
- ✅ qwen2.5-coder:7b (4.7GB) - Code specialist
- ✅ llama3.1:8b (4.9GB) - Advanced reasoning (optional)

### 2. Verify Configuration
Check `config.yaml`:
```yaml
ollama:
  multi_model:
    enabled: true
    routing:
      style: "cursor"  # Must be "cursor" not "hybrid"
```

### 3. Ensure Ollama Server Running
```bash
ollama serve
```

Keep this terminal open during testing.

---

## Test Suite

### Test 1: Simple Path - Single File Task

**Purpose:** Verify orchestrator handles simple tasks directly

**Test Case:**
```
User: Create a file hello.txt with "Hello World"
```

**Expected Behavior:**
1. TaskClassifier detects: `tier='simple'`, `file_count=1`
2. ModelRouter routes to: `simple_path`
3. Logs show: `[CURSOR-STYLE] Using orchestrator: openthinker3-7b`
4. Orchestrator generates tool call
5. Tool executes: `write_file(path='hello.txt', content='Hello World')`
6. File created successfully

**Expected VRAM:**
- openthinker3-7b loaded: ~4.7GB
- phi3:mini loaded: ~2.2GB
- **Total:** ~6.9GB ✅

**Check:**
```bash
# Monitor VRAM during execution
nvidia-smi
```

**Success Criteria:**
- ✅ File created correctly
- ✅ VRAM usage <8GB
- ✅ Execution time <10s
- ✅ Logs show orchestrator model used

---

### Test 2: Simple Path with Code - Code Delegation

**Purpose:** Verify orchestrator delegates code generation to qwen

**Test Case:**
```
User: Create a Python function to calculate factorial and save it to math_utils.py
```

**Expected Behavior:**
1. TaskClassifier detects: `tier='standard'`, `file_count=1`, `code_generation=True`
2. ModelRouter routes to: `simple_path`
3. DelegationManager decides: `delegate_code=True` (>20 lines estimated)
4. Orchestrator coordinates, qwen writes code
5. File created with valid Python function

**Expected VRAM:**
- Start: openthinker (4.7GB) + phi3 (2.2GB) = 6.9GB
- Code generation: Swap to qwen (4.7GB), phi3 stays (2.2GB) = 6.9GB
- **Max:** ~6.9GB ✅

**Success Criteria:**
- ✅ Python file created with valid syntax
- ✅ Function works correctly
- ✅ VRAM never exceeds 8GB
- ✅ Model swap time <1s (RAM caching with keep_alive)

---

### Test 3: Complex Path - Multi-File Creative Task

**Purpose:** Verify full Cursor-style complex path with planning, validation, delegation

**Test Case:**
```
User: Create a modern landing page with HTML, CSS, and JavaScript files
```

**Expected Behavior:**
1. TaskClassifier detects: `tier='complex'`, `file_count=3`, `is_creative=True`
2. ModelRouter routes to: `complex_path`
3. **PLANNING PHASE:**
   - openthinker3-7b creates detailed plan
   - PlanValidator scores plan (should be >0.7)
   - If score <0.7, PlanRefiner iterates (max 2x)
4. **EXECUTION PHASE:**
   - Orchestrator coordinates execution
   - Delegates to qwen2.5-coder:7b for code generation
   - phi3:mini formats tool calls
   - Creates 3 files: index.html, style.css, script.js
5. **MONITORING PHASE:**
   - ExecutionMonitor tracks success rate
   - Should be >90% success rate

**Expected VRAM:**
- Planning: openthinker (4.7GB) + phi3 (2.2GB) = 6.9GB
- Execution: Swap to qwen for code (4.7GB) + phi3 (2.2GB) = 6.9GB
- **Max:** ~6.9GB ✅

**Success Criteria:**
- ✅ All 3 files created
- ✅ Valid HTML, CSS, JS syntax
- ✅ Plan validation score >0.7
- ✅ Execution success rate >90%
- ✅ VRAM <8GB throughout
- ✅ Total time <60s with streaming feedback

---

### Test 4: Tool Call Reliability - phi3:mini Formatter

**Purpose:** Verify phi3:mini fixes "qwen isnt good for tool calls" issue

**Test Case:**
```
User: List all Python files in the current directory and show their sizes
```

**Expected Behavior:**
1. Orchestrator analyzes task
2. DelegationManager decides: `delegate_tools=True`
3. phi3:mini formats tool calls:
   ```
   TOOL: search_files | PARAMS: {"pattern": "*.py"}
   TOOL: get_file_size | PARAMS: {"path": "file.py"}
   ```
4. Tools execute successfully
5. Results displayed correctly

**Success Criteria:**
- ✅ Tool calls correctly formatted
- ✅ All tools execute without errors
- ✅ Results accurate
- ✅ **Compare to legacy:** Should be more reliable than qwen-only approach

---

### Test 5: VRAM Stress Test - Model Swapping

**Purpose:** Verify model swapping doesn't exceed 8GB VRAM

**Test Case:**
```
User: Create 5 Python files with different algorithms (sorting, searching, graphs, trees, dynamic programming)
```

**Expected Behavior:**
1. Complex task requires multiple model swaps
2. Orchestrator plans
3. qwen generates code for each file
4. Multiple swaps: orchestrator ↔ qwen
5. All swaps stay in VRAM budget

**VRAM Monitoring:**
```bash
# Watch VRAM in real-time
watch -n 1 nvidia-smi
```

**Success Criteria:**
- ✅ All 5 files created correctly
- ✅ **VRAM NEVER exceeds 8GB** (critical)
- ✅ Model swap time <1s (RAM caching)
- ✅ No OOM errors
- ✅ No CPU/RAM offloading (should stay on GPU)

---

### Test 6: Advanced Reasoning - Optional llama3.1:8b

**Purpose:** Verify advanced reasoning model can be used when needed

**Test Case:**
```
User: Debug this code and explain what's wrong:
def calculate(x):
    return x / 0
```

**Expected Behavior:**
1. Orchestrator detects debugging task
2. If `use_advanced_reasoning=true` in config:
   - DelegationManager delegates to llama3.1:8b (4.9GB)
   - llama3.1 provides detailed debugging analysis
3. If disabled (default):
   - Orchestrator handles directly

**Expected VRAM:**
- If llama3.1 used: ~4.9GB + phi3 (2.2GB) = ~7.1GB ✅

**Success Criteria:**
- ✅ Correctly identifies ZeroDivisionError
- ✅ Provides explanation
- ✅ VRAM <8GB
- ✅ Advanced model only used when configured

---

## Performance Benchmarks

### Expected Metrics

**Simple Path (65-70% of tasks):**
- Execution time: <15s
- VRAM usage: ~6.9GB (orchestrator + phi3)
- Model swaps: 0-1
- Success rate: >95%

**Complex Path (30-35% of tasks):**
- Execution time: 20-60s
- VRAM usage: ~6.9GB (never >8GB)
- Model swaps: 2-4 (orchestrator ↔ qwen)
- Plan validation score: >0.7
- Execution success rate: >90%

**Tool Call Reliability:**
- Before (qwen): ~70% reliable
- After (phi3): >95% reliable
- Improvement: +25 percentage points

**VRAM Optimization:**
- Max VRAM: <8GB at all times ✅
- Typical: 6.9GB (orchestrator + phi3)
- Model swap time: <1s with 32GB RAM caching
- OOM errors: 0

---

## Troubleshooting

### Issue: VRAM Exceeds 8GB

**Symptoms:**
- nvidia-smi shows >8GB VRAM
- OOM errors
- Slow execution (CPU/RAM offloading)

**Solutions:**
1. **Disable advanced reasoning:**
   ```yaml
   delegation:
     use_advanced_reasoning: false
   ```

2. **Reduce keep_alive to free VRAM between swaps:**
   ```yaml
   ollama:
     keep_alive: "10m"  # Default is 60m
   ```

3. **Check no other models loaded:**
   ```bash
   ollama ps
   ```

### Issue: Model Swaps Too Slow (>5s)

**Symptoms:**
- Model swaps take 5-8 seconds
- No RAM caching

**Solutions:**
1. **Verify keep_alive enabled:**
   ```yaml
   ollama:
     keep_alive: "60m"
   ```

2. **Check available RAM:**
   ```bash
   free -h
   ```
   Need at least 15-20GB free for model caching

3. **Restart Ollama:**
   ```bash
   ollama serve
   ```

### Issue: Tool Calls Still Unreliable

**Symptoms:**
- Tool calls malformed
- phi3:mini not being used

**Solutions:**
1. **Verify config:**
   ```yaml
   delegation:
     tool_calls_always_use_formatter: true
   ```

2. **Check logs for delegation:**
   Look for: `[CURSOR-STYLE] Using tool formatter: phi3:mini`

3. **Verify phi3:mini installed:**
   ```bash
   ollama list | grep phi3
   ```

---

## Success Criteria Summary

### ✅ Must Pass:
1. **VRAM never exceeds 8GB** (critical hardware constraint)
2. Simple path executes successfully (<15s)
3. Complex path creates multi-file projects
4. Tool calls >95% reliable (phi3:mini formatter working)
5. Model swaps <1s (RAM caching working)

### ✅ Should Pass:
6. Plan validation scores >0.7
7. Execution success rates >90%
8. Streaming progress feedback visible
9. No OOM errors during stress test
10. All 6 test cases pass

### ⚠️ Nice to Have:
11. Advanced reasoning integration works
12. Performance matches or exceeds legacy system
13. User experience feels "instant" with streaming

---

## Next Steps After Testing

### If Tests Pass:
1. ✅ Mark Cursor-style implementation complete
2. ✅ Update CLAUDE.md with new architecture docs
3. ✅ Create user guide for new features
4. ✅ Plan Phase 4 enhancements (semantic context, adaptive learning)

### If Tests Fail:
1. Review logs in `logs/agent.log`
2. Check structured logs in `logs/agent_structured.json`
3. Monitor metrics with `/metrics` command
4. Adjust configuration in `config.yaml`
5. File issues in GitHub

---

## Monitoring During Testing

### Real-Time VRAM Monitoring
```bash
# Terminal 1: Ollama server
ollama serve

# Terminal 2: VRAM monitoring
watch -n 1 nvidia-smi

# Terminal 3: Agent execution
./venv/Scripts/python agent.py
```

### Log Monitoring
```bash
# Watch logs in real-time
tail -f logs/agent.log | grep "CURSOR-STYLE"
```

### Expected Log Entries
```
[CURSOR-STYLE] Using orchestrator: openthinker3-7b
[SIMPLE PATH] Simple tier task → direct orchestration
[COMPLEX PATH] complex tier, 3 files, creative=True → full pipeline
Delegation strategy:
  code_generation: DelegationDecision(delegate_code → qwen2.5-coder:7b, ...)
  tool_formatting: DelegationDecision(delegate_tools → phi3:mini, ...)
```

---

## Hardware Specifications Reference

**Target Hardware:**
- GPU: RTX 2070 8GB VRAM
- RAM: 32GB (for model caching)
- CPU: AMD Ryzen 7 2700x (8 cores)

**Model VRAM Usage:**
- openthinker3-7b: 4.7GB
- qwen2.5-coder:7b: 4.7GB
- phi3:mini: 2.2GB
- llama3.1:8b: 4.9GB
- deepseek-r1:14b: 9.0GB (DISABLED - exceeds VRAM)

**Optimal Loading Strategy:**
- Primary: orchestrator (4.7GB) + phi3 (2.2GB) = 6.9GB
- Swap: qwen (4.7GB) + phi3 (2.2GB) = 6.9GB
- Always: <8GB VRAM ✅

---

**End of Testing Guide**
