import unittest
import io
import json
from jenkinslog import JenkinsLogParser, ApproxTokenCounter, normalize_ansi, Chunk

class TestJenkinsLogParser(unittest.TestCase):
    def test_reconstruction_invariant(self):
        log_content = "[Pipeline] stage\n[Pipeline] { (Build)\n\x1b[31mERROR\x1b[0m: foo\n"
        stream = io.StringIO(log_content)
        parser = JenkinsLogParser()
        
        chunks = list(parser.parse(stream))
        reconstructed = "".join(chunk.content for chunk in chunks)
        
        expected = "[Pipeline] stage\n[Pipeline] { (Build)\nERROR: foo\n"
        self.assertEqual(reconstructed, expected)

    def test_chunking_oversized(self):
        log_content = "[Pipeline] stage\n[Pipeline] { (Build)\n[Pipeline] sh\n+ docker build .\n"
        # add 100 lines
        for i in range(100):
            log_content += f"Step {i}\n"
        
        stream = io.StringIO(log_content)
        # small max tokens so it splits
        parser = JenkinsLogParser(max_tokens=20, overlap_lines=2)
        
        chunks = list(parser.parse(stream))
        self.assertTrue(len(chunks) > 1)
        self.assertEqual(chunks[1].context.stage, "Build")
        self.assertEqual(chunks[1].context.step, "sh")
        self.assertEqual(chunks[1].context.command, "docker build .")
        self.assertEqual(chunks[1].context.workload, "docker")
        self.assertEqual(chunks[1].docker_operation, "build")
        
        # Check continuation chunk
        self.assertTrue(chunks[2].continuation)
        self.assertTrue(len(chunks[2].previous_tail) > 0)
        
        reconstructed = "".join(chunk.content for chunk in chunks)
        
        # ensure no data loss
        expected = log_content.replace("\x1b[31m", "").replace("\x1b[0m", "") # No ANSI in test anyway
        self.assertEqual(reconstructed, expected)

    def test_npm_workload(self):
        parser = JenkinsLogParser()
        chunks = list(parser.parse_file("testdata/npm-test-failure.log"))
        
        self.assertTrue(any(c.context.workload == 'npm' for c in chunks))
        self.assertTrue(any("FAIL src/foo.test.js" in c.content for c in chunks))

    def test_docker_build(self):
        parser = JenkinsLogParser()
        chunks = list(parser.parse_file("testdata/docker-build-success.log"))
        
        self.assertTrue(any(c.context.workload == 'docker' for c in chunks))
        self.assertTrue(any(c.docker_operation == 'build' for c in chunks))
        self.assertTrue(any("#7 exporting layers" in c.content for c in chunks))
        
    def test_python_traceback(self):
        parser = JenkinsLogParser()
        chunks = list(parser.parse_file("testdata/python-traceback.log"))
        
        self.assertTrue(any(c.context.workload == 'python' for c in chunks))
        self.assertTrue(any("Traceback (most recent call last):" in c.content for c in chunks))

if __name__ == "__main__":
    unittest.main()
