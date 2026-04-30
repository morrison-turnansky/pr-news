"""Claude Code CLI execution with 2-stage approach for reliable JSON output."""

import json
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from anthropic import AnthropicVertex

if TYPE_CHECKING:
    from pr_filter.config import PRReviewConfig
    from pr_filter.data_structs import ReviewOutputSchema


def run_claude_analysis(
    prompt: str,
    workspace_path: str,
    config: "PRReviewConfig",
    timeout: int = 500,
) -> str:
    """Stage 1: Free-form PR analysis without JSON constraints.

    Args:
        prompt: Analysis prompt for Claude
        workspace_path: Path to repo workspace
        config: Configuration with Vertex AI settings
        timeout: Maximum execution time in seconds

    Returns:
        Raw text analysis from Claude

    Raises:
        ValueError: If workspace path does not exist
        RuntimeError: If Claude execution fails
    """
    workspace = Path(workspace_path).resolve()

    if not workspace.exists():
        raise ValueError(f"Workspace path does not exist: {workspace}")

    cmd = ["claude", "-p"]  # Print mode - single turn, no JSON constraint

    print("Stage 1: Analyzing PR (free-form)...")
    print(f"Workspace: {workspace}")

    env = os.environ.copy()
    env.update(config.get_vertex_env())
    env["PWD"] = str(workspace)

    result = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        cwd=str(workspace),
        env=env,
    )

    if result.returncode != 0:
        error_msg = f"Claude analysis failed (exit {result.returncode})"
        if result.stderr:
            error_msg += f"\nStderr: {result.stderr}"
        if result.stdout:
            error_msg += f"\nStdout: {result.stdout[:500]}"
        raise RuntimeError(error_msg)

    return result.stdout.strip()


def convert_to_json(
    analysis: str,
    config: "PRReviewConfig",
) -> "ReviewOutputSchema":
    """Stage 2: Convert analysis to structured JSON using Anthropic SDK.

    Note: Vertex AI does not support structured outputs (output_config parameter).
    Uses prompt engineering to request JSON format instead.

    Args:
        analysis: Free-form analysis from Stage 1
        config: Configuration with Vertex AI settings

    Returns:
        ReviewOutputSchema (on error, summary contains error message)
    """
    from pr_filter.data_structs import ReviewOutputSchema

    # Get JSON schema for reference in prompt
    json_schema = ReviewOutputSchema.model_json_schema(mode="validation")

    conversion_prompt = f"""Convert this PR review analysis into structured JSON.

ANALYSIS:
{analysis}

CRITICAL REQUIREMENTS:
- Output ONLY valid JSON - no markdown code blocks, no explanatory text
- Match this exact schema: {json.dumps(json_schema, indent=2)}
- verdict field MUST be integer: 0 (BLOCK) or 1 (PASS)
- Put all review comments into "comments" field as text
- Put overall assessment into "summary" field as text
- If no issues found, use empty strings and verdict: 1

Output the JSON object now:"""

    try:
        # Initialize Anthropic Vertex client
        client = AnthropicVertex(
            project_id=config.vertex_project_id,
            region=config.cloud_ml_region or "global",
        )

        print("Stage 2: Converting to JSON via prompt engineering...")

        # Make API call without structured outputs (not supported on Vertex AI)
        response = client.messages.create(
            model="claude-sonnet-4-5@20250929",
            max_tokens=2000,
            messages=[{"role": "user", "content": conversion_prompt}],
        )

        # Check stop_reason for issues
        if response.stop_reason == "max_tokens":
            print("WARNING: Response truncated by max_tokens limit")
            return ReviewOutputSchema(
                comments="",
                summary=f"Response truncated - increase max_tokens. Partial analysis: {analysis[:200]}",
                verdict=1,
            )

        # Extract text content
        json_text = response.content[0].text.strip()

        # Remove markdown code blocks if present
        if json_text.startswith("```"):
            lines = json_text.split("\n")
            # Remove first line (```json or ```) and last line (```)
            if len(lines) > 2:
                json_text = "\n".join(lines[1:-1])

        # Parse and validate with Pydantic
        json_data = json.loads(json_text)
        result = ReviewOutputSchema(**json_data)

        return result

    except json.JSONDecodeError as e:
        # JSON parsing failed
        print(f"WARNING: JSON parse failed: {e}")
        print(f"Response preview: {json_text[:500] if 'json_text' in locals() else 'No response'}")
        return ReviewOutputSchema(
            comments="",
            summary=f"JSON parse error: {str(e)[:100]}. Original analysis: {analysis[:200]}",
            verdict=1,
        )
    except Exception as e:
        # Other errors
        print(f"WARNING: Conversion failed: {e}")
        return ReviewOutputSchema(
            comments="",
            summary=f"Conversion error: {str(e)[:200]}. Original analysis: {analysis[:200]}",
            verdict=1,
        )


def run_claude_code(
    prompt: str,
    workspace_path: str,
    schema: dict,
    config: "PRReviewConfig",
    timeout: int = 500,
) -> "ReviewOutputSchema":
    """Execute 2-stage Claude Code analysis with reliable JSON output.

    Stage 1: Free-form analysis (no JSON constraint)
    Stage 2: Convert to structured JSON (with schema validation via SDK)

    Args:
        prompt: Review prompt for Claude
        workspace_path: Path to repo workspace
        schema: JSON schema for output validation
        config: Configuration with Vertex AI settings
        timeout: Maximum execution time in seconds (for stage 1)

    Returns:
        ReviewOutputSchema (on error, summary contains error message)

    Raises:
        ValueError: If workspace path does not exist
        RuntimeError: If analysis fails
    """
    # Stage 1: Free-form analysis
    analysis = run_claude_analysis(prompt, workspace_path, config, timeout)

    # Stage 2: Convert to JSON with SDK using structured outputs
    structured = convert_to_json(analysis, config)

    return structured
