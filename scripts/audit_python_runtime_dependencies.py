from __future__ import annotations

import ast
import importlib.util
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
LOG_DIR = ROOT / "logs"
REPORT_TXT = LOG_DIR / "python_runtime_dependencies_audit.txt"
REPORT_JSON = LOG_DIR / "python_runtime_dependencies_audit.json"

LOCAL_MODULES = {path.stem for path in SCRIPT_DIR.glob("*.py")}
LOCAL_MODULES.update(path.stem for path in ROOT.glob("*.py"))

MODULE_PACKAGE_HINTS = {
    "PIL": "Pillow",
    "cv2": "opencv-python",
    "skimage": "scikit-image",
    "yaml": "PyYAML",
}

OPTIONAL_MODULES: set[str] = set()
REQUIRED_MODULES = {"PIL"}


@dataclass
class ImportUse:
    module: str
    files: set[str] = field(default_factory=set)


@dataclass
class Audit:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    imports: dict[str, ImportUse] = field(default_factory=dict)
    optional_imports: dict[str, ImportUse] = field(default_factory=dict)
    checked_modules: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors and not self.warnings


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def stdlib_modules() -> set[str]:
    names = set(getattr(sys, "stdlib_module_names", set()))
    names.update(sys.builtin_module_names)
    names.update(
        {
            "__future__",
            "dataclasses",
            "pathlib",
            "typing",
            "typing_extensions",
        }
    )
    return names


def imported_modules_from_node(node: ast.AST) -> set[str]:
    modules: set[str] = set()
    if isinstance(node, ast.Import):
        for alias in node.names:
            modules.add(alias.name.split(".", 1)[0])
    elif isinstance(node, ast.ImportFrom):
        if not node.level and node.module:
            modules.add(node.module.split(".", 1)[0])
    return modules


def top_level_imports(path: Path, audit: Audit) -> tuple[set[str], set[str]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
    except SyntaxError as exc:
        audit.errors.append(f"Cannot parse imports from {rel(path)}: {exc}")
        return set(), set()
    except OSError as exc:
        audit.errors.append(f"Cannot read {rel(path)}: {exc}")
        return set(), set()

    modules: set[str] = set()
    optional_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modules.update(imported_modules_from_node(node))
        elif isinstance(node, ast.Try):
            caught_import_error = any(
                isinstance(handler.type, ast.Name) and handler.type.id in {"ImportError", "ModuleNotFoundError"}
                for handler in node.handlers
                if handler.type is not None
            )
            if caught_import_error:
                for child in ast.walk(ast.Module(body=node.body, type_ignores=[])):
                    if isinstance(child, (ast.Import, ast.ImportFrom)):
                        optional_modules.update(imported_modules_from_node(child))
    optional_modules = {module for module in optional_modules if module in OPTIONAL_MODULES and module not in REQUIRED_MODULES}
    return modules - optional_modules, optional_modules


def collect_imports(audit: Audit) -> None:
    stdlib = stdlib_modules()
    for path in sorted(SCRIPT_DIR.glob("*.py")):
        required, optional = top_level_imports(path, audit)
        for module in required:
            if module in stdlib or module in LOCAL_MODULES:
                continue
            audit.imports.setdefault(module, ImportUse(module=module)).files.add(rel(path))
        for module in optional:
            if module in stdlib or module in LOCAL_MODULES:
                continue
            audit.optional_imports.setdefault(module, ImportUse(module=module)).files.add(rel(path))


def check_imports(audit: Audit) -> None:
    for module in sorted(audit.imports):
        audit.checked_modules.append(module)
        if importlib.util.find_spec(module) is None:
            package = MODULE_PACKAGE_HINTS.get(module, module)
            used_by = ", ".join(sorted(audit.imports[module].files))
            audit.errors.append(f"Missing Python runtime dependency {module!r} (install package {package!r}); used by {used_by}.")
    for module in sorted(audit.optional_imports):
        audit.checked_modules.append(module)
        if importlib.util.find_spec(module) is None:
            package = MODULE_PACKAGE_HINTS.get(module, module)
            used_by = ", ".join(sorted(audit.optional_imports[module].files))
            audit.notes.append(f"Missing optional Python dependency {module!r} (package {package!r}); optional use by {used_by}.")


def write_reports(audit: Audit) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(
        json.dumps(
            {
                "passed": audit.passed,
                "errors": audit.errors,
                "warnings": audit.warnings,
                "notes": audit.notes,
                "checked_modules": audit.checked_modules,
                "imports": {
                    module: sorted(use.files)
                    for module, use in sorted(audit.imports.items())
                },
                "optional_imports": {
                    module: sorted(use.files)
                    for module, use in sorted(audit.optional_imports.items())
                },
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    lines = [
        "Python Runtime Dependencies Audit",
        "=================================",
        "",
        f"Passed: {audit.passed}",
        f"External modules checked: {len(audit.checked_modules)}",
        f"Errors: {len(audit.errors)}",
        f"Warnings: {len(audit.warnings)}",
        f"Notes: {len(audit.notes)}",
        "",
        "Errors",
        "------",
        *(f"- {item}" for item in audit.errors),
        "",
        "Warnings",
        "--------",
        *(f"- {item}" for item in audit.warnings),
        "",
        "Notes",
        "-----",
        *(f"- {item}" for item in audit.notes),
        "",
        "Modules",
        "-------",
        *(f"- {module}: {', '.join(sorted(audit.imports[module].files))}" for module in sorted(audit.imports)),
        "",
        "Optional Modules",
        "----------------",
        *(f"- {module}: {', '.join(sorted(audit.optional_imports[module].files))}" for module in sorted(audit.optional_imports)),
    ]
    REPORT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    audit = Audit()
    collect_imports(audit)
    check_imports(audit)
    write_reports(audit)
    print(REPORT_TXT.relative_to(ROOT))
    return 0 if audit.passed else 1


if __name__ == "__main__":
    sys.exit(main())
