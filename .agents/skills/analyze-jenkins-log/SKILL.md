---
name: analyze-jenkins-log
description: >-
  Analyze Jenkins Pipeline logs. Use this skill when asked to review or diagnose failures in a Jenkins console log.
---

# Analyze Jenkins Log

This skill helps you process and analyze large Jenkins Pipeline logs using the `jenkinslog.py` chunking tool. Since Jenkins logs can be extremely large, processing them through the chunker ensures you can isolate relevant errors without exceeding your context window.

## Instructions

1. **Fetch and Chunk the Log**
   If the user provides a local file path, run the script against it. You can find the script in the root of this repository.
   ```bash
   python3 jenkinslog.py --max-tokens 8000 <path-to-jenkins-log> > chunks.jsonl
   ```
   
   If the user provides a Jenkins build URL (or if you need to fetch it from the Jenkins API), use `curl` to fetch the `consoleText` and pipe it directly to the chunker. Ask the user for credentials if authentication is required.
   ```bash
   # Example without authentication
   curl -s "$JENKINS_URL/job/my-job/123/consoleText" | python3 jenkinslog.py --max-tokens 8000 > chunks.jsonl
   
   # Example with authentication
   curl -s -u "$JENKINS_USER:$JENKINS_TOKEN" "$JENKINS_URL/job/my-job/123/consoleText" | python3 jenkinslog.py --max-tokens 8000 > chunks.jsonl
   ```

2. **Filter the Chunks**
   The output is a JSONL file where each line is a chunk containing metadata and the log content. Look for chunks that indicate failure.
   You can use `jq` or `grep` to filter chunks that might contain errors, or simply inspect the last few chunks, as failures typically occur near the end of a log.

   *Example: Finding chunks with docker workload*
   ```bash
   grep '"workload": "docker"' chunks.jsonl
   ```

   *Example: Reading the last chunk*
   ```bash
   tail -n 1 chunks.jsonl | jq .
   ```

3. **Diagnose the Failure**
   Read the specific chunk's `content` property. Look at the `stage`, `step`, and `command` metadata to understand the execution context (e.g., whether it failed during a `docker build`, an `npm test`, or a shell script).

4. **Provide a Summary**
   Explain the root cause of the failure to the user based on the isolated chunk content. Do not attempt to guess failures that are not present in the log.
