# PyTorch torch.compile PR Critique

## Goal
Identify critical bugs in Dynamo/Inductor PRs with high precision.

## Decision Contract
- **Default**: PASS
- **BLOCK only if**:
  - Concrete, reproducible bug identified
  - Specific failure scenario described
  - Issue directly caused by PR changes
  - High confidence in the analysis

## Critical Issue Categories

### 1. Correctness Bugs
- Silent wrong results (incorrect computations, wrong tensor values)
- Crashes (null pointer, index out of bounds, type errors)
- Data corruption (incorrect tensor operations, memory issues)

### 2. Guard Generation Flaws
- Missed specialization opportunities leading to incorrect behavior
- Incorrect guards allowing wrong code paths
- Guard invalidation issues causing cache misses or wrong results

### 3. Graph Capture Errors
- Lost operations during symbolic execution
- Incorrect traces leading to wrong behavior
- Missing side effects that should be preserved

### 4. Codegen Bugs
- Wrong Triton code generation
- Fusion errors creating incorrect fused kernels
- Incorrect kernel arguments or memory access patterns

### 5. Concurrency Issues
- Race conditions in parallel compilation
- Deadlocks in multi-threaded scenarios
- Thread-safety violations in shared state

## NOT Critical

- Style or formatting issues
- Minor inefficiencies without correctness impact
- Hypothetical edge cases without clear trigger scenario
- General "this could be improved" feedback without concrete bug
- Documentation improvements
- Test-only changes (unless test is incorrect)

## Explanation Format (if BLOCK)

Your explanation MUST include all four elements:

1. **What changed**: Specific code modification (file, line, function)
2. **What's the flaw**: Concrete bug description (not speculation)
3. **Why incorrect**: Violates invariant, breaks API contract, causes wrong behavior
4. **When it fails**: Reproducible scenario (specific input, condition, or state)

### Good Example
```
File: torch/_dynamo/guards.py, line 42
What changed: Modified guard generation to skip list mutation checks
What's the flaw: Guard misses when VariableTracker wraps a mutated list
Why incorrect: Cached graph assumes immutable list, but list was modified
When it fails: When a VariableTracker wraps a list that gets mutated after guard creation, the guard allows reuse of stale cached graph with wrong list contents
```

### Bad Example (Too Vague)
```
This might cause issues with guards
```

## Precision Over Recall

- **If uncertain**: PASS (not BLOCK)
- **If speculative**: PASS (not BLOCK)
- **If hypothetical**: PASS (not BLOCK)
- **If "could potentially"**: PASS (not BLOCK)

Only BLOCK if you are highly confident the issue is real and concrete.

## Self-Check Validation

If enabled, after generating a BLOCK verdict, validate with this question:

> Is this definitely a real bug with a concrete failure scenario?
> If there is any uncertainty, change verdict to PASS.

This prevents false positives from over-cautious analysis.
