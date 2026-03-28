import argparse
import sys
from pathlib import Path
from .parser import parse
from .type_checker import TypeChecker
from .transpiler import Transpiler
from .build import Builder

def main():
    parser = argparse.ArgumentParser(description="Hyper Lang compiler")
    parser.add_argument("command", choices=["build", "run", "check"], help="Command to execute")
    parser.add_argument("file", help="Input .hyper file")
    parser.add_argument("--target", help="Target triple for cross-compilation")
    parser.add_argument("--output", help="Output file/directory")
    args = parser.parse_args()

    if args.command == "build":
        builder = Builder(".")
        builder.build(Path(args.file), target=args.target)
    elif args.command == "run":
        with open(args.file, 'r', encoding='utf-8') as f:
            source = f.read()
        ast = parse(source)
        checker = TypeChecker()
        checker.check(ast)
        transpiler = Transpiler()
        transpiler.transpile(ast)
        python_code = "\n".join(transpiler.code)
        exec(python_code)
    elif args.command == "check":
        with open(args.file, 'r', encoding='utf-8') as f:
            source = f.read()
        ast = parse(source)
        checker = TypeChecker()
        checker.check(ast)
        print("Type check passed")
