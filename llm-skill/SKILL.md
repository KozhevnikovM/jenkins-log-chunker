# Jenkins Log Analyzer Skill

## Context
You are an AI assistant helping to diagnose and troubleshoot failures in Jenkins Pipeline CI/CD logs. Jenkins logs can be extremely large, making it impossible to read them directly into your context window.

To overcome this, you have access to a local Python tool called `jenkinslog.py` that parses the raw console output, extracts execution context (stages, steps, commands), and breaks the log into semantically meaningful chunks (JSONL) that fit within token limits.

## Capability Instructions
Whenever the user asks you to analyze a Jenkins log file:

1. **Do NOT try to `cat` or read the entire file directly.**
2. Instead, use your shell execution capabilities to run the chunker script provided in this skill package:
   ```bash
   python3 scripts/jenkinslog.py --max-tokens 8000 <path-to-jenkins-log> > chunks.jsonl
   ```
3. **Filter and Search the Chunks:**
   The tool outputs JSONL. Each line contains a log segment and metadata like `stage`, `step`, `command`, `workload` (e.g., docker, npm), and `docker_operation`.
   
   Since errors usually happen near the end or in specific build steps, use standard Unix tools to inspect the chunks before reading their full contents:
   - *Example: Look for chunks containing docker commands*
     `grep '"workload": "docker"' chunks.jsonl`
   - *Example: Inspect the last chunk (most likely to contain the fatal error)*
     `tail -n 1 chunks.jsonl | jq .`
   - *Example: Search for chunks with the word "error" in their content*
     `grep -i 'error' chunks.jsonl`

4. **Diagnose:**
   Once you have identified the chunk(s) containing the error, read the `content` field.
   Use the accompanying metadata (`stage`, `step`, etc.) to provide the user with precise context about where and why the build failed.

## Constraints
- Do not attempt to guess or hallucinate failures that are not present in the chunked log output.
- Always preserve the context when explaining the issue to the user.
