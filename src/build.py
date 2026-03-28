# hyperlang/build.py

import subprocess
import sys
import venv
from pathlib import Path
from typing import List

from .parser import parse
from .type_checker import TypeChecker
from .transpiler import Transpiler
from .cross_compile import CrossCompiler


class BuildError(Exception):
    pass


class Builder:
    def __init__(self, project_dir: str = "."):
        self.project_dir = Path(project_dir).resolve()
        self.build_dir = self.project_dir / "build"
        self.cache_dir = self.build_dir / "cache"
        self.venv_dir = self.cache_dir / "venv"
        self.release_dir = self.build_dir / "release"

    def prepare_dirs(self):
        """Tworzy katalogi robocze."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.release_dir.mkdir(parents=True, exist_ok=True)

    def collect_python_dependencies(self, ast) -> List[str]:
        """Zbiera zależności Pythona z importów <python:...>."""
        deps = []
        for imp in ast.imports:
            if imp.path.startswith("python:"):
                pkg = imp.path.split(":", 1)[1]
                # Jeśli ścieżka zawiera '/', bierzemy pierwszą część jako nazwę pakietu
                if "/" in pkg:
                    pkg = pkg.split("/")[0]
                deps.append(pkg)
        return deps

    def create_venv_and_install(self, dependencies: List[str]):
        """Tworzy virtualenv i instaluje zależności."""
        if not dependencies:
            return
        # Tworzenie venv, jeśli nie istnieje
        if not self.venv_dir.exists():
            venv.create(self.venv_dir, with_pip=True)
        # Wybór ścieżki do pip w zależności od systemu
        if sys.platform == "win32":
            pip_path = self.venv_dir / "Scripts" / "pip"
        else:
            pip_path = self.venv_dir / "bin" / "pip"
        # Instalacja każdej zależności
        for dep in dependencies:
            print(f"Installing Python dependency: {dep}")
            subprocess.run([str(pip_path), "install", dep], check=True)

    def compile_to_python(self, hyper_file: Path):
        """Transpiluje .hyper do Pythona, sprawdza typy, instaluje zależności i zapisuje plik .py."""
        with open(hyper_file, "r", encoding="utf-8") as f:
            source = f.read()
        ast = parse(source)

        # Sprawdzanie typów
        checker = TypeChecker()
        checker.check(ast)

        # Zbieranie zależności Pythona
        py_deps = self.collect_python_dependencies(ast)
        if py_deps:
            self.create_venv_and_install(py_deps)

        # Transpilacja
        transpiler = Transpiler()
        transpiler.venv_path = self.venv_dir   # przekazujemy ścieżkę do venv (używana w importach)
        transpiler.transpile(ast)
        python_code = "\n".join(transpiler.code)

        py_file = self.cache_dir / f"{hyper_file.stem}.py"
        with open(py_file, "w", encoding="utf-8") as f:
            f.write(python_code)

        return py_file, py_deps

    def build_with_pyoxidizer(self, py_file: Path, dependencies: List[str], target_triple: str = None):
        """Uruchamia PyOxidizer, aby zbudować statyczną binarkę."""
        cross = CrossCompiler()
        if target_triple:
            cross.set_target_triple(target_triple)
        cross.check_cross_compile_prerequisites()

        config = cross.generate_pyoxidizer_config(py_file, self.release_dir,
                                                  self.cache_dir, self.venv_dir, dependencies)
        config_path = self.cache_dir / "pyoxidizer.toml"
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(config)

        try:
            subprocess.run(["pyoxidizer", "build", "--path", str(config_path)],
                           check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            raise BuildError(f"PyOxidizer failed:\n{e.stderr}")

    def build(self, hyper_file: str, target: str = None):
        """Główna metoda budowania."""
        hyper_path = Path(hyper_file).resolve()
        if not hyper_path.exists():
            raise BuildError(f"File not found: {hyper_path}")

        self.prepare_dirs()
        py_file, py_deps = self.compile_to_python(hyper_path)
        self.build_with_pyoxidizer(py_file, py_deps, target)
        print(f"✅ Binary built in {self.release_dir}")
