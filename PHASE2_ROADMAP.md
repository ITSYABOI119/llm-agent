# Phase 2 Implementation Roadmap
## Foundation: Execution History & Error Recovery

**Status:** Day 1 In Progress
**Started:** 2025-10-10
**Estimated Duration:** 3 days (10-13 hours)

---

## Overview

Phase 2 builds the foundation for system learning and automatic error recovery. By tracking all executions and implementing intelligent recovery strategies, the agent becomes self-improving and more reliable.

**Key Goals:**
- 📊 Track execution history for learning
- 🔧 Automatic error recovery (60-70% of common errors)
- 🧠 Adaptive routing based on real usage
- 📈 Performance optimization over time

---

## Day 1: Execution History Database (3-4 hours)

### ✅ Completed:
1. **Created execution_history.py** - SQLite database with comprehensive tracking
   - executions table (task details, routing, results)
   - tool_results table (individual tool tracking)
   - Query interface (recent, errors, stats, misroutes)

### 🔄 In Progress:
2. **Integrate history logging into executors**
   - Add to single_phase.py execute() method
   - Add to two_phase.py execute() method
   - Track: start time, end time, success/failure, tool calls

### ⏳ Pending:
3. **Add execution_history config section**
   ```yaml
   execution_history:
     enabled: true
     database_path: "logs/execution_history.db"
     retention_days: 90
     track_tool_details: true
   ```

4. **Test history logging**
   - Run simple task, verify DB entry
   - Run two-phase task, verify DB entry
   - Check error logging works
   - Query stats and verify output

**Time Estimate:** 2 hours remaining

---

## Day 2: Error Recovery (4-5 hours)

### Components to Build:

1. **error_classifier.py** (~30 min)
   ```python
   class ErrorClassifier:
       def classify_error(error_message, context) -> Dict:
           # Returns: {type, severity, recoverable, strategy}
           # Types: syntax_error, file_not_found, timeout,
           #        permission_denied, rate_limit, model_error
   ```

2. **error_recovery.py** (~2 hours)
   - RecoveryStrategyExecutor class
   - Strategies:
     - SyntaxErrorRecovery: Re-prompt with error context
     - PathErrorRecovery: Create missing directories
     - TimeoutRecovery: Retry with smaller scope
     - RateLimitRecovery: Exponential backoff

3. **Integration** (~1.5 hours)
   - Wrap executor calls with try/except
   - On error: classify → select strategy → attempt recovery
   - Log recovery attempts to history
   - Max 3 retries per error type

4. **Testing** (~1 hour)
   - Force syntax error, verify recovery
   - Force missing path, verify recovery
   - Force timeout, verify graceful degradation
   - Check history records recovery attempts

**Deliverables:**
- tools/error_classifier.py
- tools/error_recovery.py
- Updated executors with recovery hooks
- Test cases demonstrating recovery

---

## Day 3: Adaptive Learning (3-4 hours)

### Components to Build:

1. **adaptive_analyzer.py** (~2 hours)
   ```python
   class AdaptiveAnalyzer:
       def analyze_routing_performance() -> Dict:
           # Query history, identify patterns
           # Returns: suggested threshold adjustments

       def detect_misroutes() -> List[Dict]:
           # Find tasks that failed with chosen route
           # Suggest alternative routing rules

       def recommend_model_for_task(task_analysis) -> str:
           # ML-lite: Success rate per model per complexity
           # Recommend best model based on history
   ```

2. **CLI Commands** (~1 hour)
   - `/history` - Show recent executions
   - `/history stats` - Performance metrics
   - `/history errors` - Recent error patterns
   - `/analyze routing` - Routing performance analysis
   - `/analyze misroutes` - Identify problematic routes

3. **Integration** (~30 min)
   - Optional: Auto-apply threshold adjustments (with approval)
   - Manual: Present recommendations to user
   - Config flag: `adaptive_routing.auto_adjust_thresholds: false`

4. **Testing** (~30 min)
   - Create diverse execution history
   - Run analysis commands
   - Verify recommendations make sense
   - Test misroute detection

**Deliverables:**
- tools/adaptive_analyzer.py
- CLI commands for history analysis
- Documentation in CLAUDE.md
- Example analysis outputs

---

## Success Metrics

### Phase 2 Complete When:
- ✅ Execution history database functional
- ✅ All executions logged automatically
- ✅ Error recovery working for 3+ error types
- ✅ Recovery success rate >60%
- ✅ Adaptive analyzer provides recommendations
- ✅ CLI commands accessible
- ✅ Documentation updated
- ✅ All tests passing

### Performance Targets:
- **Error Recovery:** 60-70% automatic recovery
- **Database Overhead:** <50ms per execution
- **History Query Speed:** <100ms for stats
- **Misroute Detection:** Identify issues after 5+ failures

---

## File Checklist

### New Files:
- [x] tools/execution_history.py (450 lines)
- [ ] tools/error_classifier.py (~200 lines)
- [ ] tools/error_recovery.py (~400 lines)
- [ ] tools/adaptive_analyzer.py (~300 lines)
- [x] PHASE2_ROADMAP.md (this file)

### Modified Files:
- [ ] tools/executors/single_phase.py (+50 lines)
- [ ] tools/executors/two_phase.py (+50 lines)
- [ ] config.yaml (+20 lines)
- [ ] agent.py (+30 lines for CLI commands)
- [ ] CLAUDE.md (Phase 2 section)

### Test Files:
- [ ] tests/test_execution_history.py
- [ ] tests/test_error_recovery.py
- [ ] tests/test_adaptive_analyzer.py

---

## Risk Management

### Potential Issues:
1. **Database Lock Contention**
   - Mitigation: Use write-ahead logging (WAL mode)
   - Mitigation: Async logging option

2. **Recovery Loop (infinite retries)**
   - Mitigation: Max retries per error type
   - Mitigation: Track recovery attempts in DB

3. **Bad Threshold Recommendations**
   - Mitigation: Manual approval required
   - Mitigation: Minimum sample size (10+ executions)

4. **Performance Overhead**
   - Mitigation: Optional (can disable)
   - Mitigation: Async logging
   - Mitigation: Batch inserts

---

## Dependencies

### Required:
- SQLite3 (built-in Python)
- Existing Phase 1 features (streaming, routing)

### Optional:
- Redis (for L2 cache - Phase 3)
- ML libraries (for advanced predictions - Phase 3+)

---

## Testing Strategy

### Unit Tests:
- ExecutionHistory methods
- ErrorClassifier edge cases
- Recovery strategies individually

### Integration Tests:
- End-to-end execution with history logging
- Error → classify → recover → log flow
- Multi-error recovery scenarios

### Manual Tests:
- Force various error types
- Verify recovery success
- Check history queries
- Test CLI commands

---

## Next Steps After Phase 2

**Phase 3: Advanced Features (Week 2)**
- Semantic context engine (RAG improvements)
- Dependency graph builder
- Plan validator + refiner
- Execution monitoring + feedback loop

**Phase 4: Polish (Days 13-14)**
- Comprehensive testing
- Performance tuning
- Production deployment prep
- Documentation finalization

---

## Current Progress

**Overall Phase 2:** 10% complete
- Day 1: 33% (1/3 tasks done)
- Day 2: 0% (not started)
- Day 3: 0% (not started)

**Time Spent:** 1 hour
**Time Remaining:** ~9-12 hours

---

**Last Updated:** 2025-10-10
**Next Session:** Continue Day 1 - Integrate history logging into executors
