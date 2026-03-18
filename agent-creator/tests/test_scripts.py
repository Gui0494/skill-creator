#!/usr/bin/env python3
"""
Unit tests for agent-creator scripts.

Run:
    python -m pytest agent-creator/tests/ -v
    # or without pytest:
    python agent-creator/tests/test_scripts.py
"""

import json
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Ensure scripts are importable
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from validate_agent import parse_frontmatter, validate_frontmatter, validate_structure, validate_agent
from preflight import check_python_version, check_disk_space, check_write_permission


# ─── Test helpers ────────────────────────────────────────────────────

class TestResult:
    def __init__(self, name):
        self.name = name
        self.passed = False
        self.error = None

    def __repr__(self):
        status = "PASS" if self.passed else "FAIL"
        detail = f" - {self.error}" if self.error else ""
        return f"[{status}] {self.name}{detail}"


def create_temp_agent(name="test-agent", description="Test agent", extra_content="", scripts=None, extra_files=None):
    """Create a temporary agent directory for testing."""
    tmp = tempfile.mkdtemp()
    agent_dir = Path(tmp) / name
    agent_dir.mkdir()

    skill_md = f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n\n{extra_content}"
    (agent_dir / "SKILL.md").write_text(skill_md)

    if scripts:
        scripts_dir = agent_dir / "scripts"
        scripts_dir.mkdir()
        for fname, content in scripts.items():
            (scripts_dir / fname).write_text(content)

    if extra_files:
        for fpath, content in extra_files.items():
            full_path = agent_dir / fpath
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)

    return tmp, agent_dir


# ─── parse_frontmatter tests ────────────────────────────────────────

def test_parse_frontmatter_valid():
    t = TestResult("parse_frontmatter: valid basic frontmatter")
    try:
        content = "---\nname: my-agent\ndescription: Does stuff\n---\n\n# Content"
        fm = parse_frontmatter(content)
        assert fm is not None, "Expected dict, got None"
        assert fm["name"] == "my-agent", f"Expected 'my-agent', got '{fm.get('name')}'"
        assert fm["description"] == "Does stuff", f"Expected 'Does stuff', got '{fm.get('description')}'"
        t.passed = True
    except Exception as e:
        t.error = str(e)
    return t


def test_parse_frontmatter_multiline():
    t = TestResult("parse_frontmatter: multiline description with |")
    try:
        content = "---\nname: my-agent\ndescription: |\n  First line\n  Second line\n---\n\n# Content"
        fm = parse_frontmatter(content)
        assert fm is not None, "Expected dict, got None"
        assert "First line" in fm["description"], f"Missing 'First line' in '{fm['description']}'"
        assert "Second line" in fm["description"], f"Missing 'Second line' in '{fm['description']}'"
        t.passed = True
    except Exception as e:
        t.error = str(e)
    return t


def test_parse_frontmatter_no_frontmatter():
    t = TestResult("parse_frontmatter: content without frontmatter")
    try:
        fm = parse_frontmatter("# Just a heading\n\nSome content")
        assert fm is None, "Expected None for content without frontmatter"
        t.passed = True
    except Exception as e:
        t.error = str(e)
    return t


def test_parse_frontmatter_empty_values():
    t = TestResult("parse_frontmatter: keys with empty values")
    try:
        content = "---\nname: \ndescription: \n---\n"
        fm = parse_frontmatter(content)
        assert fm is not None, "Expected dict, got None"
        assert fm["name"] == "", f"Expected empty string, got '{fm.get('name')}'"
        t.passed = True
    except Exception as e:
        t.error = str(e)
    return t


# ─── validate_frontmatter tests ─────────────────────────────────────

def test_validate_frontmatter_valid():
    t = TestResult("validate_frontmatter: valid content has no errors")
    try:
        content = "---\nname: my-agent\ndescription: A good description\n---\n\n# Content"
        errors = validate_frontmatter(content)
        critical = [e for e in errors if e[0] == "CRITICAL"]
        error = [e for e in errors if e[0] == "ERROR"]
        assert len(critical) == 0, f"Unexpected critical errors: {critical}"
        assert len(error) == 0, f"Unexpected errors: {error}"
        t.passed = True
    except Exception as e:
        t.error = str(e)
    return t


def test_validate_frontmatter_missing_name():
    t = TestResult("validate_frontmatter: missing name is CRITICAL")
    try:
        content = "---\ndescription: Something\n---\n"
        errors = validate_frontmatter(content)
        critical_msgs = [msg for sev, msg in errors if sev == "CRITICAL"]
        assert any("name" in m.lower() for m in critical_msgs), f"Expected missing name error, got: {critical_msgs}"
        t.passed = True
    except Exception as e:
        t.error = str(e)
    return t


def test_validate_frontmatter_bad_name():
    t = TestResult("validate_frontmatter: uppercase name is ERROR")
    try:
        content = "---\nname: MyAgent\ndescription: Something\n---\n"
        errors = validate_frontmatter(content)
        error_msgs = [msg for sev, msg in errors if sev == "ERROR"]
        assert any("kebab" in m.lower() for m in error_msgs), f"Expected kebab-case error, got: {error_msgs}"
        t.passed = True
    except Exception as e:
        t.error = str(e)
    return t


def test_validate_frontmatter_angle_brackets():
    t = TestResult("validate_frontmatter: angle brackets in description is ERROR")
    try:
        content = "---\nname: my-agent\ndescription: Use <this> tag\n---\n"
        errors = validate_frontmatter(content)
        error_msgs = [msg for sev, msg in errors if sev == "ERROR"]
        assert any("angle" in m.lower() for m in error_msgs), f"Expected angle bracket error, got: {error_msgs}"
        t.passed = True
    except Exception as e:
        t.error = str(e)
    return t


def test_validate_frontmatter_no_frontmatter():
    t = TestResult("validate_frontmatter: no frontmatter is CRITICAL")
    try:
        errors = validate_frontmatter("# Just content\n")
        assert len(errors) > 0, "Expected at least one error"
        assert errors[0][0] == "CRITICAL", f"Expected CRITICAL, got {errors[0][0]}"
        t.passed = True
    except Exception as e:
        t.error = str(e)
    return t


# ─── validate_structure tests ───────────────────────────────────────

def test_validate_structure_valid_agent():
    t = TestResult("validate_structure: valid agent passes")
    tmp = None
    try:
        tmp, agent_dir = create_temp_agent(
            scripts={"helper.py": "#!/usr/bin/env python3\n\"\"\"Helper.\"\"\"\nprint('hi')\n"},
            extra_files={"references/guide.md": "# Guide\n"},
            extra_content="See references/guide.md for details.\n"
        )
        errors = validate_structure(agent_dir)
        critical = [e for e in errors if e[0] == "CRITICAL"]
        assert len(critical) == 0, f"Unexpected critical errors: {critical}"
        t.passed = True
    except Exception as e:
        t.error = str(e)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    return t


def test_validate_structure_missing_skillmd():
    t = TestResult("validate_structure: missing SKILL.md is CRITICAL")
    tmp = None
    try:
        tmp = tempfile.mkdtemp()
        agent_dir = Path(tmp) / "empty-agent"
        agent_dir.mkdir()
        errors = validate_structure(agent_dir)
        assert len(errors) > 0, "Expected errors"
        assert errors[0][0] == "CRITICAL", f"Expected CRITICAL, got {errors[0][0]}"
        assert "SKILL.md" in errors[0][1], f"Expected SKILL.md mention, got: {errors[0][1]}"
        t.passed = True
    except Exception as e:
        t.error = str(e)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    return t


def test_validate_structure_sensitive_file():
    t = TestResult("validate_structure: .env file is CRITICAL")
    tmp = None
    try:
        tmp, agent_dir = create_temp_agent(
            extra_files={".env": "SECRET=abc123\n"}
        )
        errors = validate_structure(agent_dir)
        critical = [e for e in errors if e[0] == "CRITICAL" and "ensitive" in e[1]]
        assert len(critical) > 0, f"Expected sensitive file detection, errors: {errors}"
        t.passed = True
    except Exception as e:
        t.error = str(e)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    return t


def test_validate_structure_missing_shebang():
    t = TestResult("validate_structure: script without shebang is WARNING")
    tmp = None
    try:
        tmp, agent_dir = create_temp_agent(
            scripts={"no_shebang.py": "print('no shebang')\n"}
        )
        errors = validate_structure(agent_dir)
        warnings = [e for e in errors if e[0] == "WARNING" and "shebang" in e[1]]
        assert len(warnings) > 0, f"Expected shebang warning, errors: {errors}"
        t.passed = True
    except Exception as e:
        t.error = str(e)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    return t


def test_validate_structure_broken_reference():
    t = TestResult("validate_structure: broken reference is ERROR")
    tmp = None
    try:
        tmp, agent_dir = create_temp_agent(
            extra_content="See references/nonexistent.md for details.\n"
        )
        errors = validate_structure(agent_dir)
        ref_errors = [e for e in errors if e[0] == "ERROR" and "Referenced" in e[1]]
        assert len(ref_errors) > 0, f"Expected reference error, errors: {errors}"
        t.passed = True
    except Exception as e:
        t.error = str(e)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    return t


# ─── validate_agent API tests ───────────────────────────────────────

def test_validate_agent_api():
    t = TestResult("validate_agent: returns (True, msg) for valid agent")
    tmp = None
    try:
        tmp, agent_dir = create_temp_agent()
        is_valid, message = validate_agent(agent_dir)
        assert is_valid is True, f"Expected valid, got: {message}"
        t.passed = True
    except Exception as e:
        t.error = str(e)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    return t


# ─── preflight tests ────────────────────────────────────────────────

def test_preflight_python_version():
    t = TestResult("preflight: python version check passes on current runtime")
    try:
        result = check_python_version((3, 8))
        assert result["passed"] is True, f"Python version check failed: {result}"
        assert "3." in result["current"], f"Unexpected version: {result['current']}"
        t.passed = True
    except Exception as e:
        t.error = str(e)
    return t


def test_preflight_python_version_future():
    t = TestResult("preflight: python version check fails for future version")
    try:
        result = check_python_version((99, 0))
        assert result["passed"] is False, "Should fail for Python 99.0"
        t.passed = True
    except Exception as e:
        t.error = str(e)
    return t


def test_preflight_disk_space():
    t = TestResult("preflight: disk space check passes with low threshold")
    try:
        result = check_disk_space(min_mb=1)
        assert result["passed"] is True, f"Disk space check failed: {result}"
        assert result["free_mb"] > 0, "Free MB should be positive"
        t.passed = True
    except Exception as e:
        t.error = str(e)
    return t


def test_preflight_write_permission():
    t = TestResult("preflight: write permission check passes on temp dir")
    tmp = None
    try:
        tmp = tempfile.mkdtemp()
        result = check_write_permission(tmp)
        assert result["passed"] is True, f"Write permission failed: {result}"
        t.passed = True
    except Exception as e:
        t.error = str(e)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    return t


# ─── Test runner ─────────────────────────────────────────────────────

ALL_TESTS = [
    # parse_frontmatter
    test_parse_frontmatter_valid,
    test_parse_frontmatter_multiline,
    test_parse_frontmatter_no_frontmatter,
    test_parse_frontmatter_empty_values,
    # validate_frontmatter
    test_validate_frontmatter_valid,
    test_validate_frontmatter_missing_name,
    test_validate_frontmatter_bad_name,
    test_validate_frontmatter_angle_brackets,
    test_validate_frontmatter_no_frontmatter,
    # validate_structure
    test_validate_structure_valid_agent,
    test_validate_structure_missing_skillmd,
    test_validate_structure_sensitive_file,
    test_validate_structure_missing_shebang,
    test_validate_structure_broken_reference,
    # validate_agent API
    test_validate_agent_api,
    # preflight
    test_preflight_python_version,
    test_preflight_python_version_future,
    test_preflight_disk_space,
    test_preflight_write_permission,
]


def run_all_tests():
    results = [test() for test in ALL_TESTS]
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    print(f"\n{'='*60}")
    print(f"Agent Creator Tests: {passed}/{len(results)} passed")
    print(f"{'='*60}\n")

    for r in results:
        print(f"  {r}")

    if failed > 0:
        print(f"\n{failed} test(s) FAILED.")
        return 1

    print(f"\nAll {passed} tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(run_all_tests())
