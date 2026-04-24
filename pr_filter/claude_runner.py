"""Claude Code CLI execution and environment management."""

import json
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pr_filter.config import PRReviewConfig


def run_claude_code(
    prompt: str,
    workspace_path: str,
    schema: dict,
    config: "PRReviewConfig",
    timeout: int = 500,
) -> dict:
    """Execute Claude Code CLI with JSON schema validation.

    Args:
        prompt: Review prompt for Claude
        workspace_path: Path to pytorch repo workspace
        schema: JSON schema for output validation
        config: Configuration with Vertex AI settings
        timeout: Maximum execution time in seconds

    Returns:
        Parsed JSON output

    Raises:
        ValueError: If workspace path does not exist
        RuntimeError: If Claude execution fails
        subprocess.TimeoutExpired: If execution exceeds timeout
        json.JSONDecodeError: If output is not valid JSON
    """
    workspace = Path(workspace_path).resolve()

    if not workspace.exists():
        raise ValueError(f"Workspace path does not exist: {workspace}")

    cmd = [
        "claude",
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(schema),
    ]

    print("Executing Claude Code CLI...")
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
        error_msg = f"Claude Code failed (exit {result.returncode})"
        if result.stderr:
            error_msg += f"\nStderr: {result.stderr}"
        if result.stdout:
            error_msg += f"\nStdout: {result.stdout[:500]}"
        raise RuntimeError(error_msg)

    output = result.stdout.strip()

    try:
        wrapper = json.loads(output)

        # Claude CLI --output-format json returns wrapper with metadata
        # When using --json-schema, output is in "structured_output" field
        # Otherwise it's in "result" field
        if isinstance(wrapper, dict):
            # Check for structured output first (used with --json-schema)
            if "structured_output" in wrapper and wrapper["structured_output"]:
                return wrapper["structured_output"]

            # Fallback to result field
            if "result" in wrapper:
                actual_response = wrapper["result"]

                # Handle empty result - synthesize default PASS
                if not actual_response or actual_response == "":
                    duration_sec = wrapper.get("duration_ms", 0) // 1000
                    return {
                        "comments": [],
                        "summary": {
                            "total_issues": 0,
                            "critical": 0,
                            "major": 0,
                            "minor": 0,
                            "suggestions": 0,
                            "verdict": 1,
                            "explanation": (
                                f"Analysis completed ({duration_sec}s, "
                                f"{wrapper.get('num_turns', 0)} turns) but "
                                f"returned no findings. Defaulting to PASS."
                            ),
                        },
                    }

            # Parse the result (might be a JSON string)
            if isinstance(actual_response, str):
                # Strip markdown code fences if present (```json or ```)
                cleaned = actual_response.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]  # Remove ```json prefix
                    if cleaned.endswith("```"):
                        cleaned = cleaned[:-3]  # Remove ``` suffix
                    cleaned = cleaned.strip()
                elif cleaned.startswith("```"):
                    cleaned = cleaned[3:]  # Remove ``` prefix
                    if cleaned.endswith("```"):
                        cleaned = cleaned[:-3]  # Remove ``` suffix
                    cleaned = cleaned.strip()

                return json.loads(cleaned)
            else:
                return actual_response

        # If no wrapper, assume it's the direct response
        return wrapper

    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse Claude output as JSON: {e}"
        if result.stdout:
            error_msg += f"\nOutput: {result.stdout[:500]}"
        raise json.JSONDecodeError(error_msg, result.stdout, e.pos) from e
