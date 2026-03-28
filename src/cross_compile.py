# hyperlang/cross_compile.py

import subprocess
from pathlib import Path
from typing import List, Optional


class CrossCompiler:
    """Obsługa cross‑kompilacji poprzez odpowiednie ustawienie targetu dla PyOxidizer."""

    TARGETS = {
        "linux": "x86_64-unknown-linux-gnu",
        "windows": "x86_64-pc-windows-msvc",
        "android": "aarch64-linux-android",
        "macos": "x86_64-apple-darwin",
        "arm_linux": "armv7-unknown-linux-gnueabihf",
    }

    def __init__(self):
        self.target_triple: Optional[str] = None
        self.target_os: Optional[str] = None

    def set_target(self, target_os: str):
        """Ustawia docelowy system operacyjny na podstawie skróconej nazwy."""
        if target_os not in self.TARGETS:
            raise ValueError(f"Unsupported target OS: {target_os}. Available: {list(self.TARGETS.keys())}")
        self.target_os = target_os
        self.target_triple = self.TARGETS[target_os]

    def set_target_triple(self, triple: str):
        """Ustawia bezpośrednio triplet docelowy."""
        self.target_triple = triple
        self.target_os = None

    def get_target_triple(self) -> Optional[str]:
        return self.target_triple

    def generate_pyoxidizer_config(self, py_file: Path, output_dir: Path, cache_dir: Path,
                                    venv_path: Path, dependencies: List[str]) -> str:
        """Generuje plik konfiguracyjny PyOxidizer dla danego targetu."""
        config = f"""
[env]
PYTHONPATH = "{cache_dir}"

[python]
pip_install = [
"""
        for dep in dependencies:
            config += f'    "{dep}",\n'
        config += f"""
]
virtualenv = "{venv_path}"

[application]
type = "executable"
name = "{py_file.stem}"
script = "{py_file}"

[build]
target_triple = "{self.target_triple or 'host'}"
output_dir = "{output_dir}"
"""
        return config

    def check_cross_compile_prerequisites(self):
        """Sprawdza, czy narzędzia do cross‑kompilacji są dostępne (rustup target)."""
        if not self.target_triple:
            return
        try:
            result = subprocess.run(["rustup", "target", "list", "--installed"],
                                    capture_output=True, text=True, check=True)
            installed = result.stdout.splitlines()
            if self.target_triple not in installed:
                print(f"Warning: Rust target {self.target_triple} not installed. "
                      f"Run 'rustup target add {self.target_triple}'")
        except FileNotFoundError:
            print("Warning: rustup not found. Cross‑compilation may fail.")
