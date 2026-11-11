#!/usr/bin/env python3
"""
LM Studio Worker MCP Server for Antigravity CLI (agy)
Author: SidiElvalli & Gemini
License: MIT

Enables high-performance local AI code delegation via LM Studio's OpenAI-compatible API.
"""

import os
import sys
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from openai import OpenAI
import httpx

# Initialize FastMCP Server
mcp = FastMCP("LMStudioWorker")

# Configuration via environment variables with sensible defaults
BASE_URL = os.environ.get("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
API_KEY = os.environ.get("LMSTUDIO_API_KEY", "lm-studio")
DEFAULT_MODEL = os.environ.get("LMSTUDIO_MODEL", "local-model")

# HTTP and OpenAI client
client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


@mcp.tool()
def get_worker_status() -> dict:
    """
    Checks the connectivity and status of the local LM Studio instance.
    Returns endpoint URL, connection state, loaded models, and latency.
    """
    try:
        with httpx.Client(timeout=3.0) as http_client:
            resp = http_client.get(f"{BASE_URL.rstrip('/')}/models")
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("id") for m in data.get("data", [])]
                return {
                    "status": "online",
                    "base_url": BASE_URL,
                    "active_model_fallback": DEFAULT_MODEL,
                    "available_models": models,
                    "loaded_model_count": len(models),
                }
            return {
                "status": "error",
                "base_url": BASE_URL,
                "error": f"LM Studio responded with HTTP {resp.status_code}",
            }
    except Exception as exc:
        return {
            "status": "offline",
            "base_url": BASE_URL,
            "error": f"Failed to connect to LM Studio: {str(exc)}",
            "hint": "Ensure LM Studio is running and the local server is started on port 1234.",
        }


@mcp.tool()
def list_local_models() -> list[str]:
    """
    Returns the list of model identifiers currently served by LM Studio.
    """
    try:
        with httpx.Client(timeout=3.0) as http_client:
            resp = http_client.get(f"{BASE_URL.rstrip('/')}/models")
            if resp.status_code == 200:
                data = resp.json()
                return [m.get("id") for m in data.get("data", [])]
            return []
    except Exception:
        return []


@mcp.tool()
def delegate_coding_task(
    file_path: str,
    task_instructions: str,
    context_files: list[str] = [],
    model_override: str = "",
) -> str:
    """
    Delegates a scoped coding, refactoring, or file-writing task to the local LM Studio model.
    Writes the resulting code directly to file_path and returns line count verification.

    Args:
        file_path: Destination path of the file to create or overwrite.
        task_instructions: Specific code implementation instructions.
        context_files: Optional list of file paths to supply as read-only reference context.
        model_override: Optional specific model identifier (defaults to currently loaded model).
    """
    target = Path(file_path)
    current_content = target.read_text(encoding="utf-8") if target.exists() else ""

    # Gather reference context files if provided
    ref_context = ""
    for c_file in context_files:
        p = Path(c_file)
        if p.exists():
            try:
                ref_context += (
                    f"\n--- Reference File: {c_file} ---\n{p.read_text(encoding='utf-8')}\n"
                )
            except Exception as e:
                ref_context += f"\n--- Reference File: {c_file} (Read error: {e}) ---\n"

    system_prompt = (
        "You are an expert, deterministic code-generation engine.\n"
        "Output ONLY the complete, valid, raw code for the target file.\n"
        "Do NOT wrap the code in markdown backticks (```).\n"
        "Do NOT include conversational explanations or introductory remarks."
    )

    user_prompt = (
        f"{ref_context}\n"
        f"--- Target File ({file_path}) Current Content ---\n{current_content}\n\n"
        f"--- Task Instructions ---\n{task_instructions}\n\n"
        "Return the complete updated file content and nothing else."
    )

    target.parent.mkdir(parents=True, exist_ok=True)
    full_output = []
    target_model = model_override.strip() if model_override.strip() else DEFAULT_MODEL

    try:
        response = client.chat.completions.create(
            model=target_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            # Disable reasoning tokens / CoT bloat for models supporting chat_template_kwargs
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            stream=True,
        )

        for chunk in response:
            if chunk.choices and chunk.choices[0].delta:
                content = chunk.choices[0].delta.content
                if content:
                    full_output.append(content)
                    # Periodic flush to disk to ensure real-time progress
                    if len(full_output) % 25 == 0:
                        target.write_text("".join(full_output), encoding="utf-8")

    except Exception as exc:
        if not full_output:
            return (
                f"ERROR: Failed communicating with LM Studio at {BASE_URL}: {str(exc)}. "
                "Ensure LM Studio local server is running and a model is loaded."
            )

    output = "".join(full_output).strip()

    # Strip markdown backtick wrappers if model emitted them despite prompt rules
    if output.startswith("```"):
        lines = output.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        output = "\n".join(lines)

    if output:
        target.write_text(output + "\n", encoding="utf-8")
        line_count = len(output.splitlines())
        return (
            f"SUCCESS: {file_path} written by local model ({line_count} lines).\n"
            f"Target Model: {target_model} via {BASE_URL}"
        )

    return f"WARNING: Local model returned an empty response for {file_path}."


if __name__ == "__main__":
    mcp.run()
