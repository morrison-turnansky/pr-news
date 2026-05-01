"""Claude Code CLI execution with 2-stage approach for reliable JSON output."""

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

    conversion_prompt = f"""Convert this PR review analysis into structured review data.

ANALYSIS:
{analysis}

INSTRUCTIONS:
- Record all review findings using the record_review tool
- verdict: 0 for BLOCK (critical/major issues found), 1 for PASS (safe to merge)
- comments: All review comments as text (file locations, severity, descriptions)
- summary: Overall assessment and explanation of verdict
- If no issues found, use empty strings and verdict: 1"""

    try:
        # Initialize Anthropic Vertex client
        client = AnthropicVertex(
            project_id=config.vertex_project_id,
            region=config.cloud_ml_region or "global",
        )

        print("Stage 2: Converting to structured output via tool use...")

        # Force Claude to use tool for structured output (deterministic JSON)
        response = client.messages.create(
            model="claude-sonnet-4-5@20250929",
            max_tokens=2000,
            messages=[{"role": "user", "content": conversion_prompt}],
            tools=[
                {
                    "name": "record_review",
                    "description": "Record the code review results",
                    "input_schema": ReviewOutputSchema.model_json_schema(),
                }
            ],
            tool_choice={"type": "tool", "name": "record_review"},
        )

        # Extract tool use block from response
        tool_use = next(block for block in response.content if block.type == "tool_use")

        # Validate and parse structured data
        review_data = ReviewOutputSchema.model_validate(tool_use.input)

        return review_data

    except StopIteration:
        # No tool use block found in response
        print("WARNING: No tool use block found in response")
        return ReviewOutputSchema(
            comments="",
            summary=f"Tool use extraction failed. Analysis: {analysis[:200]}",
            verdict=1,
        )
    except Exception as e:
        # Validation errors or other issues
        print(f"WARNING: Tool use validation failed: {e}")
        return ReviewOutputSchema(
            comments="",
            summary=f"Validation failed: {str(e)}. Analysis: {analysis[:200]}",
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
