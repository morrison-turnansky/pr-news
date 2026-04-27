"""Claude Code CLI execution with 2-stage approach for reliable JSON output."""

import json
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

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
    """Stage 2: Convert analysis to structured JSON matching schema.

    Args:
        analysis: Free-form analysis from Stage 1
        schema: JSON schema for output
        config: Configuration with Vertex AI settings
        timeout: Maximum execution time in seconds

    Returns:
        Parsed JSON matching schema

    Raises:
        RuntimeError: If conversion fails
        json.JSONDecodeError: If output is not valid JSON
    """
    conversion_prompt = f"""Convert this PR review analysis into structured JSON.

ANALYSIS:
{analysis}

OUTPUT FORMAT (JSON schema):
{json.dumps(schema, indent=2)}

CRITICAL REQUIREMENTS:
- Output ONLY valid JSON matching the schema above
- verdict field MUST be integer: 0 (BLOCK) or 1 (PASS)
- Put all review comments into "comments" field as a text block
- Put the summary into "summary" field as text
- If no issues found, use empty strings and verdict: 1

Output the JSON now:"""

    cmd = [
        "claude",
        "-p",
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(schema),
    ]

    print("Stage 2: Converting to JSON...")

    env = os.environ.copy()
    env.update(config.get_vertex_env())

    result = subprocess.run(
        cmd,
        input=conversion_prompt,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=env,
    )

    if result.returncode != 0:
        # If conversion fails, create default structure
        print("WARNING: JSON conversion failed, creating default structure")
        return {
            "comments": "",
            "summary": f"Analysis completed but JSON conversion failed: {analysis[:200]}",
            "verdict": 1,
        }

    output = result.stdout.strip()

    try:
        wrapper = json.loads(output)

        # Claude CLI --output-format json returns wrapper with metadata
        if isinstance(wrapper, dict):
            # Check for structured output first (used with --json-schema)
            if "structured_output" in wrapper and wrapper["structured_output"]:
                return wrapper["structured_output"]

            # Fallback to result field
            if "result" in wrapper:
                actual_response = wrapper["result"]

                # Handle empty result
                if not actual_response or actual_response == "":
                    return {
                        "comments": "",
                        "summary": "No structured output from conversion",
                        "verdict": 1,
                    }

                # Parse if string
                if isinstance(actual_response, str):
                    return json.loads(actual_response)
                else:
                    return actual_response

        # If no wrapper, assume direct response
        return wrapper

    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse JSON: {e}"
        if result.stdout:
            error_msg += f"\nOutput: {result.stdout[:500]}"
        raise json.JSONDecodeError(error_msg, result.stdout, e.pos) from e


def run_claude_code(
    prompt: str,
    workspace_path: str,
    schema: dict,
    config: "PRReviewConfig",
    timeout: int = 500,
) -> dict:
    """Execute 2-stage Claude Code analysis with reliable JSON output.

    Stage 1: Free-form analysis (no JSON constraint)
    Stage 2: Convert to structured JSON (with schema validation)

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

    # Stage 2: Convert to JSON
    structured = convert_to_json(analysis, schema, config, timeout=120)

    return structured
