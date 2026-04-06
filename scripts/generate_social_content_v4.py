#!/usr/bin/env python3
"""兼容入口：请改用 generate_content.py（行为相同）。"""
import pathlib
import subprocess
import sys

p = pathlib.Path(__file__).resolve().parent / "generate_content.py"
sys.exit(subprocess.call([sys.executable, str(p)] + sys.argv[1:]))
