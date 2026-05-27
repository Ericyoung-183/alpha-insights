import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


INSTALLER = Path(__file__).resolve().parents[1] / "install_codex.py"


class CodexInstallTests(unittest.TestCase):
    def test_reinstall_replaces_target_without_sibling_backups(self) -> None:
        with tempfile.TemporaryDirectory(prefix="alpha-codex-install-") as tmp:
            codex_home = Path(tmp) / "codex"
            env = os.environ.copy()
            env["CODEX_HOME"] = str(codex_home)

            for _ in range(2):
                subprocess.run(
                    [sys.executable, str(INSTALLER), "--skip-verify"],
                    check=True,
                    env=env,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

            skills_dir = codex_home / "skills"
            alpha_entries = sorted(path.name for path in skills_dir.glob("alpha-insights*"))
            self.assertEqual(alpha_entries, ["alpha-insights"])

            hooks = json.loads((codex_home / "hooks.json").read_text(encoding="utf-8"))
            commands = [
                hook.get("command", "")
                for entries in hooks.get("hooks", {}).values()
                for entry in entries
                for hook in entry.get("hooks", [])
            ]
            install_root = codex_home / "skills" / "alpha-insights"
            self.assertIn(
                f"python3 {install_root / 'scripts/codex_hooks/alpha_insights_pre_tool.py'}",
                commands,
            )
            self.assertIn(
                f"python3 {install_root / 'scripts/codex_hooks/alpha_insights_post_tool.py'}",
                commands,
            )


if __name__ == "__main__":
    unittest.main()
