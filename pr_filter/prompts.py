"""Prompt and schema generation for Claude Code agent reviews."""

from pr_filter.data_structs import PullRequest, ReviewOutputSchema


def build_review_prompt(pr: PullRequest, skill_paths: list[str]) -> str:
    """
    Build prompt for Claude Code agent to review a PR (Stage 1: Free-form).

    The agent will use tools (Read, Grep) to explore the codebase
    and produce a thorough analysis in natural language.

    Stage 2 will convert the analysis to JSON, so this stage focuses
    on finding issues without JSON formatting constraints.

    Args:
        pr: PullRequest to review
        skill_paths: Paths to skill files for domain knowledge

    Returns:
        Prompt string for Claude Code agent
    """

    prompt = f"""Review PR #{pr.pr_number}: {pr.title}

**PR Information:**
- Author: {pr.author}
- URL: {pr.url}
- Files changed: {", ".join(pr.files_changed)}
- Created: {pr.created_at.strftime("%Y-%m-%d")}

**Your Task:**
Analyze this PR for critical bugs, correctness issues, and security vulnerabilities.
Be efficient - use tools only when necessary to understand the changes.

**Tools Available:**
- Use `Read` to examine changed files in the workspace
- Use `Grep` to search for patterns, usage, dependencies

**Analysis Focus:**
1. **Correctness**: Silent bugs, wrong results, incorrect logic
2. **Crashes**: Null pointers, index errors, type mismatches
3. **Data corruption**: Tensor operations, memory issues
4. **Concurrency**: Race conditions, deadlocks
5. **Performance**: Major regressions only
6. **Security**: Injection, DoS, privilege escalation

**Output Format:**
Provide a thorough analysis covering:
- Each issue found (file, line number, severity, what's wrong, how to fix)
- Overall assessment
- Whether the PR should be BLOCKED (verdict: 0) or PASSED (verdict: 1)

You may optionally structure it as JSON:

```json
{{
  "comments": "Detailed review comments with all issues found",
  "summary": "Overall assessment of the PR",
  "verdict": 0
}}
```

**CRITICAL: verdict field MUST be integer 0 or 1** (NOT strings "BLOCK"/"PASS")

**Verdict Criteria:**
- **verdict: 0** (BLOCK) for: silent bugs, crashes, data corruption, race conditions, security issues
- **verdict: 1** (PASS) for: style issues, minor inefficiencies, suggestions, or if no critical/major issues found

**Domain Knowledge Skills (use Read tool if needed):**
{chr(10).join(f"- {path}" for path in skill_paths) if skill_paths else "No specific domain skills provided"}

If domain-specific skill files are listed above, use the Read tool to access them for specialized guidance on the codebase architecture and common patterns.

**PR Diff:**
```diff
{pr.diff}
```

**Changed Files to Review:**
{chr(10).join(f"- {f}" for f in pr.files_changed)}

Begin your analysis now. Be thorough and specific about any issues found.
"""

    return prompt


def get_review_json_schema() -> dict:
    """
    Generate JSON schema for Claude Code review output.

    Returns:
        JSON schema dict suitable for --json-schema parameter
    """
    return ReviewOutputSchema.model_json_schema(mode="validation")
