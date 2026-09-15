# Jenkins Log Analyzer LLM Skill

This directory contains a portable "Skill Package" that empowers any LLM agent with shell access (e.g., Claude Desktop, Codex, OpenCode, Qwen) to intelligently parse and analyze massive Jenkins CI/CD logs without exceeding their context windows.

## What's Included
- `SKILL.md`: The system prompt/instructions for the LLM.
- `scripts/jenkinslog.py`: The Python chunker script that safely splits logs into semantic JSONL blocks.

## How to Use With Other Agents

1. **Provide the Files**: Copy this entire `llm-skill` folder into the workspace or environment that the AI agent has access to.
2. **Inject the Instructions**: Open `SKILL.md` and copy its contents. Paste this into the agent's custom instructions, system prompt, or simply send it as your first message in the chat.
3. **Execute**: Ask the agent to "analyze my Jenkins log at `path/to/log`". The agent will follow the instructions, run `./scripts/jenkinslog.py`, filter the JSONL output, and provide an accurate diagnosis.

## Requirements for the Agent
- Ability to execute shell commands locally.
- Access to a Python 3.11+ runtime.
