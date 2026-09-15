#!/usr/bin/env python3
import sys
import re
import json
import argparse
from dataclasses import dataclass, field, replace
from typing import Protocol, Iterator, TextIO, List, Optional, Tuple

@dataclass
class SourcePosition:
    line_start: int
    line_end: int
    byte_start: Optional[int] = None
    byte_end: Optional[int] = None

@dataclass
class Block:
    type: str
    name: Optional[str] = None

@dataclass
class JenkinsContext:
    stage: Optional[str] = None
    step: Optional[str] = None
    command: Optional[str] = None
    workload: Optional[str] = None
    branch: Tuple[str, ...] = ()
    stack: Tuple[Block, ...] = ()

@dataclass
class Chunk:
    id: str
    sequence: int
    context: JenkinsContext
    content: str
    tokens: int
    source: SourcePosition
    continuation: bool = False
    previous_tail: str = ""
    docker_operation: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "sequence": self.sequence,
        }
        if self.context.stage is not None: d["stage"] = self.context.stage
        if self.context.step is not None: d["step"] = self.context.step
        if self.context.command is not None: d["command"] = self.context.command
        if self.context.workload is not None: d["workload"] = self.context.workload
        
        d["tokens"] = self.tokens
        d["line_start"] = self.source.line_start
        d["line_end"] = self.source.line_end
        d["continuation"] = self.continuation
        
        if self.docker_operation is not None:
            d["docker_operation"] = self.docker_operation
            
        if self.previous_tail:
            d["previous_tail"] = self.previous_tail
            
        d["content"] = self.content
        return d

class TokenCounter(Protocol):
    def count(self, text: str) -> int: ...

class ApproxTokenCounter:
    def count(self, text: str) -> int:
        return max(1, len(text) // 4)

def normalize_ansi(text: str) -> str:
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

class JenkinsLogParser:
    def __init__(self, max_tokens: int = 12000, overlap_lines: int = 30, token_counter: TokenCounter = None):
        self.max_tokens = max_tokens
        self.overlap_lines = overlap_lines
        self.token_counter = token_counter or ApproxTokenCounter()
        self.seq = 0

    def parse(self, stream: TextIO) -> Iterator[Chunk]:
        context = JenkinsContext()
        lines_buffer = []
        tokens = 0
        line_start = 1
        current_line = 1
        continuation = False
        previous_tail = []
        docker_op = None
        
        # We process line by line
        for raw_line in stream:
            line = normalize_ansi(raw_line)
            # detect strong boundary (e.g. stage change)
            is_strong_boundary = False
            is_medium_boundary = False
            
            m_stage = re.search(r'\[Pipeline\] \{ \((.*?)\)', line)
            m_stage2 = re.search(r'\[Pipeline\] stage', line)
            
            if m_stage or m_stage2:
                is_strong_boundary = True

            if line.startswith('[Pipeline] sh') or line.startswith('[Pipeline] // stage'):
                is_medium_boundary = True
                
            # BuildKit boundaries
            if line.startswith('#') and ('[internal]' in line or 'RUN' in line):
                is_medium_boundary = True

            should_split = False
            if tokens > self.max_tokens:
                should_split = True
            elif is_strong_boundary and lines_buffer:
                should_split = True
            elif is_medium_boundary and tokens > (self.max_tokens * 0.8) and lines_buffer:
                should_split = True

            if should_split and lines_buffer:
                content = "".join(lines_buffer)
                self.seq += 1
                yield Chunk(
                    id=f"chunk-{self.seq:04d}",
                    sequence=self.seq,
                    context=replace(context),
                    content=content,
                    tokens=tokens,
                    source=SourcePosition(line_start=line_start, line_end=current_line-1),
                    continuation=continuation,
                    previous_tail="".join(previous_tail) if continuation else "",
                    docker_operation=docker_op
                )
                if not is_strong_boundary and not is_medium_boundary:
                    continuation = True
                    previous_tail = lines_buffer[-self.overlap_lines:] if self.overlap_lines > 0 else []
                else:
                    continuation = False
                    previous_tail = []
                    
                lines_buffer = []
                tokens = 0
                line_start = current_line
                
            # Update context
            if m_stage:
                context.stage = m_stage.group(1)
            elif re.search(r'\[Pipeline\] sh', line):
                context.step = 'sh'
            elif context.step == 'sh' and line.startswith('+ '):
                cmd = line[2:].strip()
                context.command = cmd
                # basic workload classification
                if cmd.startswith('docker'):
                    context.workload = 'docker'
                    parts = cmd.split()
                    if len(parts) > 1:
                        docker_op = parts[1] if parts[1] != 'buildx' else (parts[2] if len(parts) > 2 else 'build')
                elif cmd.startswith('npm') or cmd.startswith('npx'):
                    context.workload = 'npm'
                elif cmd.startswith('go '):
                    context.workload = 'go'
                elif cmd.startswith('python') or cmd.startswith('pytest') or cmd.startswith('pip'):
                    context.workload = 'python'
                else:
                    context.workload = 'shell'

            lines_buffer.append(line)
            tokens += self.token_counter.count(line)
            current_line += 1
            
        if lines_buffer:
            content = "".join(lines_buffer)
            self.seq += 1
            yield Chunk(
                id=f"chunk-{self.seq:04d}",
                sequence=self.seq,
                context=replace(context),
                content=content,
                tokens=tokens,
                source=SourcePosition(line_start=line_start, line_end=current_line-1),
                continuation=continuation,
                previous_tail="".join(previous_tail) if continuation else "",
                docker_operation=docker_op
            )

    def parse_file(self, filepath: str) -> Iterator[Chunk]:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            yield from self.parse(f)

def main():
    parser = argparse.ArgumentParser(description="Chunk Jenkins logs for LLMs")
    parser.add_argument("file", nargs="?", help="Input log file (stdin if omitted)")
    parser.add_argument("--max-tokens", type=int, default=12000, help="Max tokens per chunk")
    parser.add_argument("--overlap-lines", type=int, default=30, help="Overlap lines for continuation chunks")
    args = parser.parse_args()

    parser_obj = JenkinsLogParser(max_tokens=args.max_tokens, overlap_lines=args.overlap_lines)
    
    stream = sys.stdin if args.file is None else open(args.file, "r", encoding="utf-8", errors="replace")
    try:
        for chunk in parser_obj.parse(stream):
            print(json.dumps(chunk.to_dict()))
            sys.stdout.flush()
    except Exception as e:
        sys.stderr.write(f"Error parsing log: {e}\n")
        sys.exit(1)
    finally:
        if args.file is not None:
            stream.close()

if __name__ == "__main__":
    main()
