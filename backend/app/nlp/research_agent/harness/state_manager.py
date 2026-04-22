"""File-based state management for the qualitative agent harness.

Manages the directory structure, manifest lifecycle, and file I/O
for harness runs. The state root is parameterized to support future
multi-tenancy (e.g. state/{user_id}/{ticker}/).
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SPRINT_NAMES = [
    "01_business_profile",
    "02_unit_economics",
    "03_industry",
    "04_moat",
    "05_management",
    "06_peers",
    "07_risks",
    "08_thesis",
]

DEFAULT_STATE_ROOT = Path("state")
CONTRACTS_DIR = Path(__file__).parent / "contracts"


class StateManager:
    """Manages file-based state for a single ticker run."""

    def __init__(self, ticker: str, state_root: Path | None = None):
        self.ticker = ticker.upper()
        self.root = (state_root or DEFAULT_STATE_ROOT) / self.ticker

    # --- Directory setup ---

    def init_run(self) -> Path:
        """Create the full directory tree for a new run. Returns the root path."""
        self.root.mkdir(parents=True, exist_ok=True)
        for sprint in SPRINT_NAMES:
            (self.root / "sprints" / sprint).mkdir(parents=True, exist_ok=True)
        (self.root / "final").mkdir(parents=True, exist_ok=True)

        self._write_initial_manifest()
        return self.root

    # --- Manifest lifecycle ---

    def _write_initial_manifest(self) -> None:
        manifest = {
            "ticker": self.ticker,
            "started_at": _now_iso(),
            "completed_at": None,
            "status": "running",
            "total_cost_usd": 0.0,
            "total_duration_seconds": 0,
            "model_routing": {},
            "sprints": {},
        }
        self.write_json(self.root / "manifest.json", manifest)

    def read_manifest(self) -> dict[str, Any]:
        return self.read_json(self.root / "manifest.json")

    def update_manifest(self, updates: dict[str, Any]) -> dict[str, Any]:
        """Merge top-level keys into the manifest and write it back."""
        manifest = self.read_manifest()
        manifest.update(updates)
        self.write_json(self.root / "manifest.json", manifest)
        return manifest

    def update_sprint_in_manifest(
        self, sprint_name: str, sprint_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Set or update a single sprint entry in the manifest."""
        manifest = self.read_manifest()
        manifest["sprints"][sprint_name] = sprint_data
        manifest["total_cost_usd"] = sum(
            s.get("cost_usd", 0.0) for s in manifest["sprints"].values()
        )
        self.write_json(self.root / "manifest.json", manifest)
        return manifest

    def complete_run(self, status: str = "completed") -> dict[str, Any]:
        """Mark the run as finished, record completion time and total duration."""
        manifest = self.read_manifest()
        manifest["status"] = status
        manifest["completed_at"] = _now_iso()
        started = datetime.fromisoformat(manifest["started_at"])
        completed = datetime.fromisoformat(manifest["completed_at"])
        manifest["total_duration_seconds"] = (completed - started).total_seconds()
        self.write_json(self.root / "manifest.json", manifest)
        return manifest

    # --- Sprint file I/O ---

    def sprint_dir(self, sprint_name: str) -> Path:
        return self.root / "sprints" / sprint_name

    def write_builder_output(self, sprint_name: str, data: dict[str, Any]) -> Path:
        path = self.sprint_dir(sprint_name) / "builder_output.json"
        self.write_json(path, data)
        return path

    def read_builder_output(self, sprint_name: str) -> dict[str, Any]:
        return self.read_json(self.sprint_dir(sprint_name) / "builder_output.json")

    def write_eval_result(self, sprint_name: str, data: dict[str, Any]) -> Path:
        path = self.sprint_dir(sprint_name) / "eval_result.json"
        self.write_json(path, data)
        return path

    def read_eval_result(self, sprint_name: str) -> dict[str, Any]:
        return self.read_json(self.sprint_dir(sprint_name) / "eval_result.json")

    def write_builder_trace(self, sprint_name: str, data: dict[str, Any]) -> Path:
        path = self.sprint_dir(sprint_name) / "builder_trace.json"
        self.write_json(path, data)
        return path

    def copy_contract(self, sprint_name: str) -> Path:
        """Copy the frozen contract into the sprint directory."""
        src = CONTRACTS_DIR / f"{sprint_name}.json"
        dst = self.sprint_dir(sprint_name) / "contract.json"
        shutil.copy2(src, dst)
        return dst

    # --- Shared input files ---

    def write_agent_bundle(self, data: dict[str, Any]) -> Path:
        path = self.root / "agent_bundle.json"
        self.write_json(path, data)
        return path

    def read_agent_bundle(self) -> dict[str, Any]:
        return self.read_json(self.root / "agent_bundle.json")

    def write_item1_text(self, text: str) -> Path:
        path = self.root / "item1_text.txt"
        path.write_text(text, encoding="utf-8")
        return path

    def read_item1_text(self) -> str:
        return (self.root / "item1_text.txt").read_text(encoding="utf-8")

    # --- Final output files ---

    def write_executive_brief(self, markdown: str) -> Path:
        path = self.root / "final" / "EXECUTIVE_BRIEF.md"
        path.write_text(markdown, encoding="utf-8")
        return path

    def write_quality_summary(self, data: dict[str, Any]) -> Path:
        path = self.root / "final" / "quality_summary.json"
        self.write_json(path, data)
        return path

    # --- Dependency resolution ---

    def read_prior_outputs(self, sprint_name: str) -> dict[str, Any]:
        """Read builder outputs from sprints that the given sprint depends on.

        Returns a dict keyed by sprint name, e.g.
        {"01_business_profile": {...}, "03_industry": {...}}
        Only includes sprints that have a builder_output.json on disk.
        """
        deps = SPRINT_DEPENDENCIES.get(sprint_name, [])
        prior: dict[str, Any] = {}
        for dep in deps:
            path = self.sprint_dir(dep) / "builder_output.json"
            if path.exists():
                prior[dep] = self.read_json(path)
        return prior

    # --- Generic I/O helpers ---

    @staticmethod
    def write_json(path: Path, data: Any) -> None:
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    @staticmethod
    def read_json(path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    def run_exists(self) -> bool:
        return (self.root / "manifest.json").exists()


SPRINT_DEPENDENCIES: dict[str, list[str]] = {
    "01_business_profile": [],
    "02_unit_economics": ["01_business_profile"],
    "03_industry": ["01_business_profile"],
    "04_moat": ["01_business_profile", "02_unit_economics", "03_industry"],
    "05_management": ["01_business_profile"],
    "06_peers": ["03_industry"],
    "07_risks": [
        "01_business_profile",
        "02_unit_economics",
        "03_industry",
        "04_moat",
        "05_management",
        "06_peers",
    ],
    "08_thesis": [
        "01_business_profile",
        "02_unit_economics",
        "03_industry",
        "04_moat",
        "05_management",
        "06_peers",
        "07_risks",
    ],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
