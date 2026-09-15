import io
from jenkinslog import JenkinsLogParser

log_content = "[Pipeline] stage\n[Pipeline] { (Build)\n[Pipeline] sh\n+ docker build .\n"
for i in range(10):
    log_content += f"Step {i}\n"
stream = io.StringIO(log_content)
parser = JenkinsLogParser(max_tokens=20, overlap_lines=2)
for i, chunk in enumerate(parser.parse(stream)):
    print(f"--- Chunk {i} ---")
    print("Context:", chunk.context)
    print("Content:", repr(chunk.content))
