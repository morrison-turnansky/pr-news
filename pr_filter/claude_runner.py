"""Claude Code CLI execution with 2-stage approach for reliable JSON output."""

import json
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from anthropic import AnthropicVertex

if TYPE_CHECKING:
    from pr_filter.config import PRReviewConfig


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
    schema: dict,
    config: "PRReviewConfig",
    timeout: int = 120,
) -> dict:
    """Stage 2: Convert analysis to structured JSON using Anthropic SDK.

    Args:
        analysis: Free-form analysis from Stage 1
        schema: JSON schema (unused, kept for compatibility)
        config: Configuration with Vertex AI settings
        timeout: Maximum execution time in seconds

    Returns:
        Parsed JSON matching ReviewOutputSchema

    Raises:
        RuntimeError: If conversion fails
    """
    from pr_filter.data_structs import ReviewOutputSchema

    conversion_prompt = f"""Convert this PR review analysis into structured JSON.

ANALYSIS:
{analysis}

CRITICAL REQUIREMENTS:
- Output ONLY valid JSON - no markdown code blocks, no other text
- verdict field MUST be integer: 0 (BLOCK) or 1 (PASS)
- Put all review comments into "comments" field as a text block
- Put the summary into "summary" field as text
- If no issues found, use empty strings and verdict: 1

JSON Schema:
{{
  "comments": "string - all review comments",
  "summary": "string - overall assessment",
  "verdict": 0 or 1 (integer)
}}

Output ONLY the JSON object, nothing else:"""

    try:
        # Initialize Anthropic Vertex client
        client = AnthropicVertex(
            project_id=config.vertex_project_id,
            region=config.cloud_ml_region or "global",
        )

        print("Stage 2: Converting to JSON with Anthropic SDK...")

        # Make API call (Vertex AI doesn't support output_format parameter)
        response = client.messages.create(
            model="claude-sonnet-4-5@20250929",
            max_tokens=2000,
            messages=[{"role": "user", "content": conversion_prompt}],
        )

        # Extract text content
        json_text = response.content[0].text.strip()

        # Remove markdown code blocks if present
        if json_text.startswith("```"):
            # Extract JSON from markdown code block
            lines = json_text.split("\n")
            json_text = "\n".join(lines[1:-1]) if len(lines) > 2 else json_text

        # Parse JSON and validate with Pydantic
        json_data = json.loads(json_text)
        result = ReviewOutputSchema(**json_data)

        # Convert Pydantic model to dict
        return {
            "comments": result.comments,
            "summary": result.summary,
            "verdict": result.verdict,
        }

    except json.JSONDecodeError as e:
        # JSON parsing failed - show what we got
        print(f"WARNING: JSON parse failed: {e}")
        print(f"Response preview: {json_text[:500] if 'json_text' in locals() else 'No response'}")
        return {
            "comments": "",
            "summary": f"JSON parse error. Original analysis: {analysis[:200]}",
            "verdict": 1,
        }
    except Exception as e:
        # Other errors
        print(f"WARNING: SDK conversion failed: {e}")
        return {
            "comments": "",
            "summary": f"Conversion failed: {str(e)[:200]}. Original analysis: {analysis[:200]}",
            "verdict": 1,
        }


def run_claude_code(
    prompt: str,
    workspace_path: str,
    schema: dict,
    config: "PRReviewConfig",
    timeout: int = 500,
) -> dict:
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
        Parsed JSON output matching schema

    Raises:
        ValueError: If workspace path does not exist
        RuntimeError: If analysis fails
    """
    # Stage 1: Free-form analysis
    analysis = run_claude_analysis(prompt, workspace_path, config, timeout)

    # Stage 2: Convert to JSON with SDK
    structured = convert_to_json(analysis, schema, config, timeout=120)

    return structured
