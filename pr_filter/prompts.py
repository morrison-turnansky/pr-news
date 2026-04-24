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

    prompt = f"""You are reviewing PR #{pr.pr_number}: {pr.title}

🚨 MANDATORY OUTPUT REQUIREMENT 🚨
Your FINAL message MUST be ONLY the JSON review object (see Output Format below).
- MAX 5 TOOL CALLS TOTAL - After 5 tools, OUTPUT JSON IMMEDIATELY
- If you exceed 5 tool calls without JSON, you FAIL
- Better to output verdict: 1 (PASS) quickly than timeout with no JSON
- NO explanatory text before or after JSON - ONLY the JSON object

**SUCCESS = Output valid JSON within 5 tool uses**
**FAILURE = Using more than 5 tools OR not outputting JSON**

**PR Information:**
- Author: {pr.author}
- URL: {pr.url}
- Files changed: {", ".join(pr.files_changed)}
- Created: {pr.created_at.strftime("%Y-%m-%d")}

**Your Task:**
Analyze this PR for critical bugs, correctness issues, and security vulnerabilities.

**Tools Available:**
- Use `Read` to examine changed files in the workspace
- Use `Grep` to search for patterns, usage, dependencies
- **STRICT LIMIT: Maximum 5 tool calls total**
- After 5 tool calls: IMMEDIATELY output JSON (no more investigation)

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
{chr(10).join(f"- {path}" for path in skill_paths) if skill_paths else "No specific domain skills provided"}

If domain-specific skill files are listed above, use the Read tool to access them for specialized guidance on the codebase architecture and common patterns.

**⏱️ TOOL BUDGET REMINDER ⏱️**
- MAX 5 TOOL CALLS - count each Read/Grep as one call
- After 3-4 tools: prepare to wrap up
- After 5 tools: STOP and OUTPUT JSON IMMEDIATELY
- Using more than 5 tools = AUTOMATIC FAILURE

**PR Diff:**
```diff
{pr.diff}
```

**Changed Files to Review:**
{chr(10).join(f"- {f}" for f in pr.files_changed)}

Begin your analysis now.

**⚠️ ANALYSIS WORKFLOW ⚠️**

Tool Call 1-2: Read the changed files from the diff
Tool Call 3-4: Quick grep for obvious issues if needed
Tool Call 5: LAST CALL - do final check if absolutely necessary
After Tool 5: OUTPUT JSON IMMEDIATELY - NO MORE TOOLS ALLOWED

**If no issues found after 3-4 tools:** Output JSON with verdict: 1 (PASS) immediately

**🚨 FINAL JSON OUTPUT REQUIREMENTS 🚨**
Your LAST message must be ONLY the JSON object:
- No markdown fences (no ```json)
- No explanation text before or after
- Just the raw JSON with "comments" and "summary" fields

**CRITICAL:** If you use more than 5 tools, you have FAILED this task
"""

    return prompt


def get_review_json_schema() -> dict:
    """
    Generate JSON schema for Claude Code review output.

    Returns:
        JSON schema dict suitable for --json-schema parameter
    """
    return ReviewOutputSchema.model_json_schema(mode="validation")
