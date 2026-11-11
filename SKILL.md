---
name: lmstudio-worker
description: Delegate scoped Python coding and refactoring tasks to local LLMs in LM Studio via the FastMCP bridge.
---

# LM Studio Worker Skill

This skill allows Antigravity (`agy`) agents to offload repetitive code generation, drafting, and file authoring to offline local models running in LM Studio.

## Architecture

- **Role Division**:
  - **Antigravity (Cloud / Architect)**: High-level reasoning, system architecture, test planning, syntax verification (`ast.parse`), and quality control.
  - **LM Studio (Local / Worker)**: Fast offline code generation for targeted files without consuming cloud API quotas.
- **MCP Bridge**: Communicates over `http://localhost:1234/v1` using FastMCP.

## Delegation Rules

1. **Keep Tasks Scoped**:
   - Limit delegated requests to small, modular files (under 100 lines).
   - Pass only strictly relevant reference files in `context_files`.
2. **Prevent Reasoning Loops**:
   - When delegating to reasoning models (e.g., Qwen 2.5 / 3.x), thinking tokens are suppressed via `extra_body={"chat_template_kwargs": {"enable_thinking": False}}`.
3. **Verify Programmatically**:
   - Check generated files using AST checks or unit test execution (`python -c "import ast; ast.parse(...)"`) rather than full-context reads.
