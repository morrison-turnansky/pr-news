"""Agentic PR critique using Claude via Vertex AI."""

import re
from pathlib import Path
from pr_filter.models import PullRequest, CritiquedPR
from pr_filter.config import PRReviewConfig

# Import VertexAI from pytorch-jira-bot
try:
    from pytorch_jira_bot.sync.vertex import VertexAI
except ImportError:
    # Fallback for testing without pytorch-jira-bot installed
    VertexAI = None


def critique_pr(pr: PullRequest, reduced_diff: str, config: PRReviewConfig) -> CritiquedPR:
    """
    Analyze PR using Claude with fresh agent pattern.

    Fresh agent pattern: Each PR gets completely isolated, stateless API call.
    One API call per PR, rebuild full prompt every time.

    Args:
        pr: PullRequest to analyze
        reduced_diff: Reduced diff from diff_reducer
        config: Configuration with model params and skill paths

    Returns:
        CritiquedPR with verdict (BLOCK or PASS), confidence, and explanation
    """
    # Load skills
    skills_content = load_skills(config.skill_paths)

    # Build full prompt (instructions + skills + diff)
    prompt = build_prompt(pr, reduced_diff, skills_content, config)

    # Fresh agent API call (isolated, stateless)
    try:
        vertex = VertexAI() if VertexAI else None
        if not vertex:
            # Fallback for testing
            return CritiquedPR(
                pr_number=pr.pr_number,
                title=pr.title,
                url=pr.url,
                files_changed=pr.files_changed,
                diff=pr.diff,
                created_at=pr.created_at,
                updated_at=pr.updated_at,
                author=pr.author,
                verdict="PASS",
                confidence=None,
                issue_explanation="",
                reduced_diff_lines=len(reduced_diff.splitlines())
            )

        response = vertex.generate_content(
            prompt=prompt,
            temperature=config.model_params.temperature,
            max_tokens=config.model_params.max_tokens
        )

        # Parse response
        verdict, confidence, explanation = parse_response(response)

        # Optional self-check validation
        if config.self_check_enabled and verdict == "BLOCK":
            verdict, confidence, explanation = self_check(
                vertex, pr, reduced_diff, skills_content, explanation, config
            )

    except Exception as e:
        # API error handling: skip PR, continue pipeline
        print(f"WARNING: API error for PR #{pr.pr_number}: {e}")
        # Default to PASS on error
        verdict = "PASS"
        confidence = None
        explanation = ""

    # Build CritiquedPR result
    return CritiquedPR(
        pr_number=pr.pr_number,
        title=pr.title,
        url=pr.url,
        files_changed=pr.files_changed,
        diff=pr.diff,
        created_at=pr.created_at,
        updated_at=pr.updated_at,
        author=pr.author,
        verdict=verdict,
        confidence=confidence,
        issue_explanation=explanation if verdict == "BLOCK" else "",
        reduced_diff_lines=len(reduced_diff.splitlines())
    )


def load_skills(skill_paths: list[str]) -> str:
    """
    Load skill files from absolute paths.

    Args:
        skill_paths: List of paths to skill .md files

    Returns:
        Combined skills content as string
    """
    skills = []

    for skill_path in skill_paths:
        try:
            # Handle both absolute and relative paths
            path = Path(skill_path)
            if not path.is_absolute():
                # Try relative to current working directory
                path = Path.cwd() / skill_path

            if path.exists():
                with open(path, 'r') as f:
                    skills.append(f.read())
            else:
                print(f"WARNING: Skill file not found: {skill_path}")
        except Exception as e:
            print(f"WARNING: Failed to load skill {skill_path}: {e}")

    return "\n\n---\n\n".join(skills)


def build_prompt(pr: PullRequest, reduced_diff: str, skills: str, config: PRReviewConfig) -> str:
    """
    Build full prompt: instructions + skills + diff.

    Args:
        pr: PullRequest being analyzed
        reduced_diff: Reduced diff text
        skills: Combined skills content
        config: Configuration

    Returns:
        Complete prompt string
    """
    prompt = f"""You are reviewing a PyTorch PR for critical bugs in torch.compile (Dynamo/Inductor).

**Your Task**: Analyze this PR and determine if it introduces a critical bug.

**Decision Contract**:
- Default: PASS
- BLOCK only if:
  - Issue is concrete and reproducible (not speculation)
  - Failure scenario is clearly defined (specific input, condition, scenario)
  - Issue is directly caused by the PR (not pre-existing)
  - High confidence in the analysis
- If any uncertainty → PASS

**Critical Issue Categories**:
1. Correctness bugs (silent wrong results, incorrect logic)
2. Crashes (null pointer, index out of bounds, type errors)
3. Data corruption (incorrect tensor operations, memory issues)
4. API contract violations (breaking changes, incorrect semantics)
5. Concurrency bugs (race conditions, deadlocks)

**NOT Critical**:
- Style or formatting issues
- Minor inefficiencies
- Hypothetical edge cases without clear trigger
- General "this could be improved" feedback

**Skills and Domain Knowledge**:
{skills}

**PR Information**:
- PR Number: {pr.pr_number}
- Title: {pr.title}
- Files Changed: {', '.join(pr.files_changed)}

**Diff (Reduced to relevant changes)**:
```diff
{reduced_diff}
```

**Instructions**:
1. Analyze the diff carefully
2. Identify any critical bugs according to the criteria above
3. Respond in this exact format:

Verdict: BLOCK or PASS
Confidence: HIGH or MEDIUM
Explanation: [If BLOCK: detailed explanation with (1) what changed, (2) what's the flaw, (3) why incorrect, (4) when it fails. If PASS: leave blank or brief note]

**Remember**: Default to PASS unless you are highly confident of a concrete, reproducible bug.
"""

    return prompt


def parse_response(response: str) -> tuple[str, str | None, str]:
    """
    Parse Claude response to extract verdict, confidence, explanation.

    Args:
        response: Raw response string from Claude

    Returns:
        Tuple of (verdict, confidence, explanation)
        - verdict: "BLOCK" or "PASS"
        - confidence: "HIGH", "MEDIUM", or None
        - explanation: Detailed explanation string (if BLOCK)
    """
    # Default to PASS if parsing fails
    verdict = "PASS"
    confidence = None
    explanation = ""

    # Extract verdict
    verdict_match = re.search(r'Verdict:\s*(BLOCK|PASS)', response, re.IGNORECASE)
    if verdict_match:
        verdict = verdict_match.group(1).upper()

    # Extract confidence
    confidence_match = re.search(r'Confidence:\s*(HIGH|MEDIUM)', response, re.IGNORECASE)
    if confidence_match:
        confidence = confidence_match.group(1).upper()

    # Extract explanation
    explanation_match = re.search(r'Explanation:\s*(.+)', response, re.DOTALL | re.IGNORECASE)
    if explanation_match:
        explanation = explanation_match.group(1).strip()

    return verdict, confidence, explanation


def self_check(
    vertex: 'VertexAI',
    pr: PullRequest,
    reduced_diff: str,
    skills: str,
    original_explanation: str,
    config: PRReviewConfig
) -> tuple[str, str | None, str]:
    """
    Perform self-check validation on BLOCK verdicts.

    Asks Claude: "Is this definitely a real bug? If any uncertainty, change to PASS."

    Args:
        vertex: VertexAI instance (already created)
        pr: PullRequest being analyzed
        reduced_diff: Reduced diff
        skills: Skills content
        original_explanation: Original BLOCK explanation
        config: Configuration

    Returns:
        Tuple of (final_verdict, final_confidence, final_explanation)
    """
    self_check_prompt = f"""You previously identified a potential bug in PR #{pr.pr_number}.

**Original Analysis**:
{original_explanation}

**Self-Check Question**:
Is this definitely a real bug with a concrete failure scenario?

**Validation Criteria**:
- Is the failure scenario specific and reproducible?
- Is the issue directly caused by this PR (not pre-existing)?
- Is there high confidence this will cause actual problems?

**If there is ANY uncertainty**, change the verdict to PASS.

**Respond in this format**:
Verdict: BLOCK or PASS
Confidence: HIGH or MEDIUM
Explanation: [Updated explanation if needed]
"""

    try:
        response = vertex.generate_content(
            prompt=self_check_prompt,
            temperature=config.model_params.temperature,
            max_tokens=config.model_params.max_tokens
        )

        verdict, confidence, explanation = parse_response(response)
        return verdict, confidence, explanation

    except Exception as e:
        print(f"WARNING: Self-check failed for PR #{pr.pr_number}: {e}")
        # Keep original verdict on self-check failure
        return "BLOCK", None, original_explanation
