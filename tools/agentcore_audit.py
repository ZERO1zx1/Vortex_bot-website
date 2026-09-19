"""AgentCore runner for THIS repository — real deterministic evidence, no fake executor.

Integrates the AgentCore framework (provider-agnostic, budget-aware, resumable)
with a genuine :class:`OperationExecutor` that performs **real local
deterministic operations** and returns verifiable evidence:

===============  ===============================================================
Work unit type   Real operation performed
===============  ===============================================================
parse            RepositoryProcessor.inspect + fingerprint_repository (real scan)
code             `git status --porcelain` + `git diff --stat` (real workspace state)
test             pytest + compileall + `node --check` (real exit codes + output tail)
polish           structure audit: root layout, tracked-file junk scan, JSON validity
output           consolidated factual report (no invented results)
===============  ===============================================================

Every ``output_text`` is captured command output, which AgentCore persists as a
real artifact under ``.agentcore/``. No provider/LLM is called, so there is no
provider-confirmed cost: ``cost_source`` stays ``estimate`` and is reported as
such.

Usage (from the repository root)::

    python tools/agentcore_audit.py .
    python tools/agentcore_audit.py . --mode CREDIT_SAFE --budget 5 --task-id aether_audit

The AgentCore installation is located via the ``AGENTCORE_HOME`` environment
variable, falling back to the standard local skills path.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict

DEFAULT_AGENTCORE_HOME = Path.home() / ".cline" / "skills" / "AgentCore"


def locate_agentcore_home() -> Path:
    """Resolve the AgentCore installation directory (env override first)."""
    candidates = []
    env_home = os.environ.get("AGENTCORE_HOME")
    if env_home:
        candidates.append(Path(env_home))
    candidates.append(DEFAULT_AGENTCORE_HOME)
    candidates.append(Path.home() / ".agents" / "skills" / "AgentCore")
    for path in candidates:
        if (path / "src" / "core" / "engine.py").is_file():
            return path
    raise SystemExit(
        "AgentCore installation not found. Set AGENTCORE_HOME to the folder "
        "containing src/core/engine.py"
    )


def _pid_alive(pid: int) -> bool:
    """Best-effort liveness check for a lock holder PID (no hard dependency)."""
    if pid <= 0:
        return False
    try:
        import psutil  # available in this project's requirements.txt
        return psutil.pid_exists(pid)
    except ImportError:
        import ctypes
        if os.name != "nt":
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        kernel32.CloseHandle(handle)
        return True


def run_cmd(cmd, cwd: Path, timeout: int = 300) -> Dict[str, Any]:
    """Run a real command and capture exit code + bounded output (no shell)."""
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True,
            timeout=timeout, errors="replace",
        )
        code = proc.returncode
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
    except subprocess.TimeoutExpired:
        code, out, err = -1, "", f"TIMEOUT after {timeout}s"
    except FileNotFoundError as exc:
        code, out, err = -2, "", f"NOT FOUND: {exc}"
    return {
        "cmd": " ".join(str(c) for c in cmd),
        "exit_code": code,
        "seconds": round(time.perf_counter() - started, 2),
        "stdout_tail": out[-3000:],
        "stderr_tail": err[-1500:],
    }


def _fmt_run(r: Dict[str, Any]) -> str:
    return (
        f"$ {r['cmd']}\n"
        f"  exit={r['exit_code']} ({r['seconds']}s)\n"
        f"  stdout:\n{r['stdout_tail'] or '  (empty)'}\n"
        + (f"  stderr:\n{r['stderr_tail']}\n" if r["stderr_tail"] else "")
    )


def build_executor(repo: Path):
    """Build a real OperationExecutor bound to ``repo`` (AgentCore must be importable)."""
    from src.core.executor import OperationExecutor
    from src.core.execution_result import ExecutionResult

    class WorkspaceEvidenceExecutor(OperationExecutor):
        """Real deterministic executor: every result is captured command output."""

        def __init__(self, repo_path: Path):
            self.repo = Path(repo_path).resolve()
            self.evidence: Dict[str, Any] = {}

        # ---- real operations -------------------------------------------------
        def _inspect(self) -> str:
            from src.ingestion.repository import RepositoryProcessor
            info = RepositoryProcessor.inspect(str(self.repo))
            fp = RepositoryProcessor.fingerprint_repository(str(self.repo))
            relevant = RepositoryProcessor.relevant_source_files(str(self.repo), max_files=25)
            self.evidence["file_count"] = info["file_count"]
            self.evidence["fingerprint"] = fp
            lines = [
                "REAL REPOSITORY INSPECTION",
                f"path: {info['path']}",
                f"file_count: {info['file_count']}",
                f"fingerprint_sha256: {fp}",
                f"git_clean: {info['git_clean']}",
                f"extensions: {info['extensions']}",
                f"entry_point_candidates: {info['entry_point_candidates']}",
                f"test_directories: {info['test_directories']}",
                f"manifests_present: {sorted(info['manifests'].keys())}",
                "",
                "top_level_files:",
                *[f"  - {f}" for f in info["files_top_level"]],
                "",
                "first 25 relevant source files:",
                *[f"  - {f}" for f in relevant],
            ]
            return "\n".join(lines)

        def _implementation(self) -> str:
            r1 = run_cmd(["git", "status", "--porcelain"], self.repo, 60)
            r2 = run_cmd(["git", "--no-pager", "diff", "--stat"], self.repo, 120)
            r3 = run_cmd(["git", "log", "--oneline", "-5"], self.repo, 60)
            self.evidence["git_status_exit"] = r1["exit_code"]
            self.evidence["working_tree_dirty"] = bool(r1["stdout_tail"])
            return (
                "REAL WORKSPACE STATE (code changes already applied in this tree)\n\n"
                + _fmt_run(r1) + "\n" + _fmt_run(r2) + "\n" + _fmt_run(r3)
            )

        def _validation(self) -> str:
            py = sys.executable or "python"
            checks = [
                run_cmd([py, "-m", "pytest", "tests", "-q"], self.repo, 600),
                run_cmd([py, "-m", "compileall", "-q", "src", "backend", "tools",
                         "tests", "main.py"], self.repo, 300),
                run_cmd(["node", "--check", "website/js/app.js"], self.repo, 120),
                run_cmd(["node", "--check", "website/js/commands.js"], self.repo, 120),
                run_cmd(["node", "--check", "website/js/config.js"], self.repo, 120),
            ]
            results = {c["cmd"]: c["exit_code"] for c in checks}
            self.evidence["validation"] = results
            all_ok = all(c["exit_code"] == 0 for c in checks)
            return (
                f"REAL VALIDATION — all_passed={all_ok}\n"
                f"exit codes: {results}\n\n"
                + "\n".join(_fmt_run(c) for c in checks)
            )

        def _polish(self) -> str:
            py = sys.executable or "python"
            import json as _json
            r1 = run_cmd(["git", "ls-files"], self.repo, 120)
            r2 = run_cmd([py, "-X", "utf8", "tools/check_cog_coverage.py"], self.repo, 300)
            tracked = [line for line in r1["stdout_tail"].splitlines() if line.strip()]
            junk = [f for f in tracked if any(
                part in f for part in ("__pycache__", ".pytest_cache", ".firebase", ".log")
            )]
            json_bad = []
            for rel in [f for f in tracked if f.endswith(".json")]:
                p = self.repo / rel
                if not p.is_file():
                    continue
                try:
                    _json.loads(p.read_text(encoding="utf-8"))
                except Exception as exc:  # noqa: BLE001 — reported, not hidden
                    json_bad.append(f"{rel}: {exc}")
            self.evidence["tracked_files"] = len(tracked)
            self.evidence["tracked_junk"] = junk
            self.evidence["json_invalid"] = json_bad
            readme = self.repo / "README.md"
            readme_ok = ("Project Structure" in readme.read_text(encoding="utf-8")
                         if readme.is_file() else False)
            return (
                "REAL STRUCTURE / HYGIENE AUDIT\n"
                f"tracked_files: {len(tracked)}\n"
                f"tracked_junk_files: {junk or 'NONE'}\n"
                f"invalid_json_files: {json_bad or 'NONE'}\n"
                f"readme_has_structure_section: {readme_ok}\n"
                f"root_entries: {sorted(p.name for p in self.repo.iterdir())}\n\n"
                + _fmt_run(r2)
            )

        def _output(self) -> str:
            v = self.evidence.get("validation") or {}
            return (
                "CONSOLIDATED FACTUAL REPORT (built only from real command results)\n"
                f"repo: {self.repo}\n"
                f"file_count: {self.evidence.get('file_count')}\n"
                f"fingerprint_sha256: {self.evidence.get('fingerprint')}\n"
                f"tracked_files: {self.evidence.get('tracked_files')}\n"
                f"tracked_junk_files: {self.evidence.get('tracked_junk')}\n"
                f"invalid_json_files: {self.evidence.get('json_invalid')}\n"
                f"validation_exit_codes: {v}\n"
                f"validation_all_passed: {all(c == 0 for c in v.values()) if v else None}\n"
                f"working_tree_dirty: {self.evidence.get('working_tree_dirty')}\n"
                f"provider_calls_made: 0 (deterministic local operations only)\n"
            )

        # ---- OperationExecutor contract -------------------------------------
        def execute(self, unit_type, model_id, prompt, context=None) -> ExecutionResult:
            started = time.perf_counter()
            try:
                if unit_type in ("parse", "inspect"):
                    text = self._inspect()
                elif unit_type == "code":
                    text = self._implementation()
                elif unit_type in ("test", "validation"):
                    text = self._validation()
                elif unit_type == "polish":
                    text = self._polish()
                elif unit_type == "output":
                    text = self._output()
                else:
                    text = self._inspect()
                ok, err = True, ""
            except Exception as exc:  # noqa: BLE001 — surfaced as a real failed unit
                ok, text, err = False, "", f"{type(exc).__name__}: {exc}"

            return ExecutionResult(
                success=ok,
                output_text=text,
                usage={"input_tokens": 0, "output_tokens": 0},
                provider="local-deterministic",
                model_id=model_id,
                error=err,
                metadata={
                    "real_operation": True,
                    "seconds": round(time.perf_counter() - started, 2),
                    # No provider called -> engine keeps cost_source == "estimate".
                },
            )

    return WorkspaceEvidenceExecutor(repo)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Run AgentCore (real deterministic evidence) against this repository.",
    )
    p.add_argument("repo", nargs="?", default=".", help="Repository root (default: .)")
    p.add_argument("--mode", default="AUTO", choices=["AUTO", "FULL", "CREDIT_SAFE"])
    p.add_argument("--budget", type=float, default=5.0, help="Budget for the run (estimates only)")
    p.add_argument("--unit", default="USD", help="Budget unit label")
    p.add_argument("--task-id", default=None, help="Task id (default: derived from fingerprint)")
    p.add_argument("--resume", default=None, help="Resume an existing task id")
    p.add_argument("--prompt", default=None, help="Override the task prompt")
    p.add_argument("--force", action="store_true",
                   help="Ignore a stale AgentCore lock file for this task id")
    p.add_argument("--reset", action="store_true",
                   help="Drop this task's checkpoint/artifacts and start fresh "
                        "(recovery from a FAILED-after-invalidation task)")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        raise SystemExit(f"Not a directory: {repo}")

    home = locate_agentcore_home()
    sys.path.insert(0, str(home))

    from src.core.engine import AgentCoreEngine
    from src.core.modes import ExecutionMode
    from src.core.task import TaskInput

    executor = build_executor(repo)
    engine = AgentCoreEngine(executor=executor)

    task_id = args.resume or args.task_id
    if not task_id:
        from src.ingestion.repository import RepositoryProcessor
        fp = RepositoryProcessor.fingerprint_repository(str(repo))
        task_id = f"aether_audit_{fp[:12]}"

    prompt = args.prompt or (
        "Audit and validate this repository: inspect the full folder structure and files, "
        "confirm the applied bug fixes, run the real test/compile/lint validation, and "
        "report the resulting folder structure hygiene."
    )

    task = TaskInput(
        prompt=prompt,
        task_id=task_id,
        repository=str(repo),
        output_type="report",
        execution_mode=ExecutionMode.from_str(args.mode),
        budget=args.budget,
        budget_unit=args.unit,
        resume_task_id=args.resume,
    )

    # Engine writes .agentcore/ relative to the CWD: pin it to the repo root.
    os.chdir(repo)

    if args.reset:
        # Recovery path: a task that AgentCore marked FAILED after an
        # invalidation cannot self-heal (attempt counters survive the status
        # reset), so drop the checkpoint and start clean under the same id.
        import shutil
        ckpt = Path(".agentcore") / "checkpoints" / f"{task_id}_manifest.json"
        if ckpt.exists():
            ckpt.unlink()
            print(f"[agentcore] --reset: removed checkpoint {ckpt}")
        task_dir = Path(".agentcore") / "tasks" / task_id
        if task_dir.is_dir():
            shutil.rmtree(task_dir)
            print(f"[agentcore] --reset: removed artifacts {task_dir}")
        args.resume = None

    # One writer per checkpoint file: concurrent runs on the same task id were
    # observed to interleave manifest writes (FAILED + wiped completed_work).
    lock_path = Path(".agentcore") / f".{task_id}.lock"
    lock_is_stale = False
    if lock_path.exists():
        try:
            holder_pid = int(lock_path.read_text(encoding="utf-8").strip() or "0")
        except (OSError, ValueError):
            holder_pid = 0
        lock_is_stale = not _pid_alive(holder_pid)
    if lock_path.exists() and not lock_is_stale and not args.force:
        raise SystemExit(
            f"Another AgentCore run appears active for task '{task_id}' "
            f"({lock_path}). Use a different --task-id, wait for it to finish, "
            f"or pass --force if you know the lock is stale."
        )
    if lock_is_stale:
        print(f"[agentcore] removing stale lock (owner pid is gone): {lock_path}")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(str(os.getpid()), encoding="utf-8")
    try:
        return _run_locked(args, repo, engine, task, task_id)
    finally:
        lock_path.unlink(missing_ok=True)


def _run_locked(args, repo: Path, engine, task, task_id: str) -> int:
    from src.output.manager import OutputManager

    manifest = engine.initialize_task(task)
    print(f"[agentcore] task_id={manifest.task_id} repo={repo}")
    print(f"[agentcore] mode={manifest.execution_mode} units={manifest.progress['total_units']} "
          f"budget={manifest.budget_info['initial']} {manifest.budget_info['unit']}")

    report = engine.run_to_completion()
    report_path = OutputManager.save_report(engine.current_manifest)

    m = engine.current_manifest
    print(f"[agentcore] status={m.status} reason={m.reason}")
    print(f"[agentcore] completed_units={len(m.completed_work)} skipped="
          f"{[u.id for u in engine.work_units if u.status == 'skipped']}")
    print(f"[agentcore] artifacts={len(m.outputs)}")
    print(f"[agentcore] report={report_path}")
    print(f"[agentcore] checkpoint={Path(engine.checkpoint_manager.checkpoint_dir) / (m.task_id + '_manifest.json')}")
    print("-" * 70)
    print(report)

    return 0 if m.status == "COMPLETED" else 1


if __name__ == "__main__":
    raise SystemExit(main())