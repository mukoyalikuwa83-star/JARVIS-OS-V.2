"""Verify lazy action mappings reference real source files and exports."""

import ast
import unittest
from pathlib import Path

from actions.lazy_loader import ACTION_HANDLERS


ROOT = Path(__file__).resolve().parent.parent


def _top_level_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig", errors="replace"))
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names.update(target.id for target in targets if isinstance(target, ast.Name))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
    return names


class LazyActionWiringTests(unittest.TestCase):
    def test_all_lazy_action_targets_exist_and_export_the_mapped_name(self):
        self.assertGreaterEqual(len(ACTION_HANDLERS), 90)
        for action, (module, attribute) in ACTION_HANDLERS.items():
            with self.subTest(action=action):
                source = ROOT.joinpath(*module.split(".")).with_suffix(".py")
                self.assertTrue(source.is_file(), f"{action} points to missing module {module}")
                if attribute:
                    self.assertIn(
                        attribute,
                        _top_level_names(source),
                        f"{action} points to missing export {module}.{attribute}",
                    )


if __name__ == "__main__":
    unittest.main()
