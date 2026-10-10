"""Positive/negative tests for domestic secret rules + hook simulation."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from secret_scanner import scan_text, list_rules


def has_rule(text, rule):
    return any(f["rule"] == rule for f in scan_text(text))


class TestPositive(unittest.TestCase):
    def test_deepseek(self):
        self.assertTrue(scan_text("key = sk-" + "a" * 32))

    def test_kimi(self):
        self.assertTrue(scan_text("kimi=" + "sk-" + "Ab3" * 16))

    def test_dashscope(self):
        self.assertTrue(scan_text("dashscope sk-" + "f" * 32))

    def test_zhipu(self):
        self.assertTrue(scan_text("zhipu key " + "A" * 32 + "." + "B" * 16))

    def test_minimax_jwt(self):
        self.assertTrue(scan_text("minimax eyJ" + "a" * 10 + "." + "b" * 10 + "." + "c" * 10))

    def test_baidu(self):
        self.assertTrue(scan_text("token ALTAK-AbCdEfGh1234"))

    def test_baichuan(self):
        self.assertTrue(scan_text("baichuan sk-" + "Z9" * 16))

    def test_db_uri(self):
        self.assertTrue(scan_text("mysql://admin:S3cr3t!@db.local:3306/app"))

    def test_private_key(self):
        self.assertTrue(scan_text("-----BEGIN RSA PRIVATE KEY-----"))

    def test_rules_listed(self):
        self.assertGreaterEqual(len(list_rules()), 10)


class TestNegative(unittest.TestCase):
    def test_placeholder(self):
        self.assertEqual(scan_text('key = "sk-your-key-here"'), [])

    def test_env_read(self):
        self.assertEqual(scan_text('key = os.getenv("DEEPSEEK_API_KEY")'), [])

    def test_normal_comment(self):
        self.assertEqual(scan_text("# hello world, no secrets here"), [])

    def test_hook_simulation_block(self):
        diff = "+\tkey = sk-" + "a" * 32 + "\n"
        findings = scan_text(diff)
        self.assertTrue(findings)
        self.assertEqual(1 if findings else 0, 1)


if __name__ == "__main__":
    unittest.main()
