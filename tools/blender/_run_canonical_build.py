"""Wrapper that runs build_all from run_module_pipeline.py inside Blender CLI.

Usage:
    blender --background --python tools/blender/_run_canonical_build.py
"""

from __future__ import annotations

import os
import sys


def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def main() -> int:
    repo = _repo_root()
    os.chdir(repo)
    pipeline_path = os.path.join(repo, "tools", "blender", "run_module_pipeline.py")
    namespace: dict = {"__file__": pipeline_path, "__name__": "__build_canonical__"}
    with open(pipeline_path, "r", encoding="utf-8") as fh:
        source = fh.read()
    exec(compile(source, pipeline_path, "exec"), namespace)
    out = namespace["build_all"](repo)
    print("build_all ok_count=", out.get("ok_count"), "fail_count=", out.get("fail_count"))
    return 0 if out.get("fail_count", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
