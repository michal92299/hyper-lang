# hyperlang/extern.py

import platform
from typing import List, Optional


class ExternLibrary:
    """Reprezentuje bibliotekę zewnętrzną do załadowania."""
    def __init__(self, kind: str, linkage: str, name: str, path: Optional[str] = None):
        self.kind = kind          # "c", "cpp", "rust", "java", "lua"
        self.linkage = linkage    # "static" or "dynamic"
        self.name = name
        self.path = path


class ExternManager:
    def __init__(self):
        self.libraries: List[ExternLibrary] = []

    def add_library(self, kind: str, linkage: str, name: str, path: Optional[str] = None):
        self.libraries.append(ExternLibrary(kind, linkage, name, path))

    def generate_imports(self) -> List[str]:
        """Zwraca listę linii kodu Pythona, które ładują zewnętrzne biblioteki."""
        imports = []
        for lib in self.libraries:
            if lib.kind == "c":
                imports.extend(self._gen_c_import(lib))
            elif lib.kind == "cpp":
                imports.extend(self._gen_cpp_import(lib))
            elif lib.kind == "rust":
                imports.extend(self._gen_rust_import(lib))
            elif lib.kind == "java":
                imports.extend(self._gen_java_import(lib))
            elif lib.kind == "lua":
                imports.extend(self._gen_lua_import(lib))
            else:
                raise ValueError(f"Unsupported extern kind: {lib.kind}")
        return imports

    def _gen_c_import(self, lib: ExternLibrary) -> List[str]:
        lines = []
        lines.append("import ctypes")
        if lib.path:
            lines.append(f"_c_lib_{lib.name} = ctypes.CDLL(r'{lib.path}')")
        else:
            if platform.system() == "Windows":
                lib_name = f"{lib.name}.dll"
            else:
                lib_name = f"lib{lib.name}.so"
            lines.append(f"_c_lib_{lib.name} = ctypes.CDLL('{lib_name}')")
        return lines

    def _gen_cpp_import(self, lib: ExternLibrary) -> List[str]:
        # Zakładamy, że funkcje są zadeklarowane jako extern "C"
        lines = []
        lines.append("import ctypes")
        if lib.path:
            lines.append(f"_cpp_lib_{lib.name} = ctypes.CDLL(r'{lib.path}')")
        else:
            if platform.system() == "Windows":
                lib_name = f"{lib.name}.dll"
            else:
                lib_name = f"lib{lib.name}.so"
            lines.append(f"_cpp_lib_{lib.name} = ctypes.CDLL('{lib_name}')")
        return lines

    def _gen_rust_import(self, lib: ExternLibrary) -> List[str]:
        # Biblioteki Rust z PyO3 – importujemy jako normalny moduł Pythona
        return [f"import {lib.name}  # external Rust library (PyO3)"]

    def _gen_java_import(self, lib: ExternLibrary) -> List[str]:
        lines = []
        lines.append("import jpype")
        lines.append("import jpype.imports")
        if lib.path:
            lines.append(f"jpype.startJVM(jpype.getDefaultJVMPath(), '-Djava.class.path={lib.path}')")
        else:
            lines.append("jpype.startJVM()")
        lines.append(f"from {lib.name} import *")
        return lines

    def _gen_lua_import(self, lib: ExternLibrary) -> List[str]:
        lines = []
        lines.append("import lupa")
        lines.append("_lua = lupa.LuaRuntime(unpack_returned_tuples=True)")
        if lib.path:
            lines.append(f"_lua.execute('package.cpath = package.cpath .. \";{lib.path}/?.so\"')")
            lines.append(f"_lua.execute('require \"{lib.name}\"')")
        else:
            lines.append(f"_lua.execute('require \"{lib.name}\"')")
        return lines
