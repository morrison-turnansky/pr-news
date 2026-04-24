"""Prompt and schema generation for Claude Code agent reviews."""

from pr_filter.data_structs import PullRequest, ReviewOutputSchema


def build_review_prompt(pr: PullRequest, skill_paths: list[str]) -> str:
    """
    Build prompt for Claude Code agent to review a PR.

    The agent will use tools (Read, Grep) to explore the codebase
    and produce structured JSON output.

    CRITICAL: The JSON example MUST use integer values for verdict field:
    - "verdict": 0 (for BLOCK)
    - "verdict": 1 (for PASS)
    DO NOT use strings like "BLOCK" or "PASS" - this will cause
    error_max_structured_output_retries due to schema mismatch.

    Args:
        pr: PullRequest to review
        skill_paths: Paths to skill files for domain knowledge

    Returns:
        Prompt string for Claude Code agent
    """

    prompt = f"""You are reviewing PyTorch PR #{pr.pr_number}: {pr.title}

**⏰ CRITICAL TIME REQUIREMENT - READ FIRST ⏰**
- HARD DEADLINE: 5 minutes (300 seconds) total
- After 4 minutes (8-10 tool uses): STOP investigating and OUTPUT JSON immediately
- Your FINAL message MUST be the JSON review object - this is MANDATORY
- Partial analysis + JSON = SUCCESS ✓
- Complete analysis + no JSON = FAILURE ✗

**SUCCESS CRITERIA:**
1. You output valid JSON before timeout (REQUIRED)
2. JSON contains your analysis findings (can be minimal)
3. If no issues found, output verdict: 1 (PASS) with brief explanation

**FAILURE (do not do this):**
- Investigating thoroughly but forgetting to output JSON
- Running out of time before outputting JSON
- Ending conversation without JSON output

**PR Information:**
- Author: {pr.author}
- URL: {pr.url}
- Files changed: {", ".join(pr.files_changed)}
- Created: {pr.created_at.strftime("%Y-%m-%d")}

**Your Task:**
Analyze this PR for critical bugs in torch.compile (Dynamo/Inductor).

**Tools Available:**
- Use `Read` to examine changed files in /workspace/pytorch
- Use `Grep` to search for patterns, usage, dependencies
- Explore the codebase to understand context
- **Be strategic**: Max 8-10 tool uses total - focus only on high-risk areas
- **Stop investigating** after 8 tool calls - prepare to output JSON

**Review Focus:**
1. **Correctness**: Silent bugs, wrong results, incorrect logic
2. **Crashes**: Null pointers, index errors, type mismatches
3. **Data corruption**: Tensor operations, memory issues
4. **Concurrency**: Race conditions, deadlocks
5. **Performance**: Major regressions only
6. **Security**: Injection, DoS, privilege escalation

**Output Format:**
Respond with ONLY a valid JSON object in this exact format:

```json
{{
  "comments": [
    {{
      "file": "relative/path/from/repo/root.py",
      "line": 42,
      "severity": "critical",
      "category": "correctness",
      "message": "Detailed description of the issue",
      "suggestion": "How to fix it (optional)",
      "verdict": 0
    }}
  ],
  "summary": {{
    "total_issues": 5,
    "critical": 1,
    "major": 2,
    "minor": 1,
    "suggestions": 1,
    "verdict": 0,
    "explanation": "Overall assessment of the PR"
  }}
}}
```

**CRITICAL: verdict field MUST be integer 0 or 1, NOT strings "BLOCK"/"PASS"**

**Field Value Requirements:**
- **severity**: Must be one of: "critical", "major", "minor", "suggestion" (string)
- **category**: Must be one of: "correctness", "performance", "security", "style" (string)
- **verdict**: Must be 0 or 1 (integer, NOT string)

**Verdict Guidelines (MUST be integer 0 or 1):**
- **verdict: 0** (BLOCK) for: silent bugs, crashes, data corruption, race conditions, security issues
- **verdict: 1** (PASS) for: style issues, minor inefficiencies, suggestions, speculative concerns

**Severity Guidelines (string):**
- **critical**: Silent bugs, crashes, data corruption, security
- **major**: Incorrect behavior, race conditions, major regressions
- **minor**: Inefficiencies, code quality, best practices
- **suggestion**: Style, refactoring ideas, optimization hints

**Default Behavior:**
- Assume verdict: 1 (PASS) unless highly confident of a concrete, reproducible bug
- Only use verdict: 0 (BLOCK) on critical or major issues with clear failure scenarios
- Avoid speculation - issues must be demonstrable

**Domain Knowledge Skills (use Read tool if needed):**
{chr(10).join(f"- {path}" for path in skill_paths) if skill_paths else "No specific skills available"}

If you need domain-specific guidance on PyTorch Dynamo or Inductor internals, use the Read tool to access these skill files.

**⏱️ TIME CHECK REMINDER ⏱️**
Remember: You must output JSON within 5 minutes. Budget your tool usage:
- Max 8-10 tool calls total
- After 6-7 tools: start wrapping up
- After 8-9 tools: OUTPUT JSON NOW
- Better to output verdict: 1 (PASS) quickly than timeout with no JSON

**PR Diff:**
```diff
{pr.diff}
```

**Changed Files to Review:**
{chr(10).join(f"- {f}" for f in pr.files_changed)}

Begin your analysis now.

**⚠️ ANALYSIS WORKFLOW - FOLLOW THIS ⚠️**

Phase 1: Quick scan (2-3 minutes, ~5-6 tool uses)
- Read changed files
- Grep for critical patterns if needed
- Identify potential issues

Phase 2: Decision point (after 3-4 minutes or 7-8 tool uses)
- If you've found issues: OUTPUT JSON NOW
- If still investigating: Do 1-2 more critical checks only
- DO NOT continue deep investigation

Phase 3: OUTPUT (MANDATORY - do this by 4 minutes)
- Stop all investigation
- Output JSON with findings (even if analysis is incomplete)
- Even if uncertain: output verdict: 1 (PASS) with explanation of what you checked

**🚨 FINAL REMINDER 🚨**
Your LAST message MUST be ONLY the JSON object.
- No markdown fences (no ```json)
- No explanation text before or after
- Just the raw JSON with "comments" and "summary" fields

If you are reading this reminder: CHECK YOUR TURN COUNT
- If you've used 8+ tool calls: OUTPUT JSON IMMEDIATELY
- If you've used 6-7 tool calls: Do ONE more check then OUTPUT JSON
- Do not exceed 10 tool uses without outputting JSON
"""

    return prompt


def get_review_json_schema() -> dict:
    """
    Generate JSON schema for Claude Code review output.

    Returns:
        JSON schema dict suitable for --json-schema parameter
    """
    return ReviewOutputSchema.model_json_schema(mode="validation")
