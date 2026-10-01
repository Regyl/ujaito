"""Package placement rules and a ban on schema statements in Python."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from archunitpython import assert_passes, project_files
from archunitpython.files.assertion.custom_file_logic import FileInfo

ROOT = str(Path(__file__).resolve().parents[1])
_DDL = re.compile(r"\b(ALTER|CREATE)\s+TABLE\b", re.IGNORECASE)


def _in_package(file: FileInfo, package: str) -> bool:
    return package in Path(file.path).parts


def _class_defs(file: FileInfo) -> list[ast.ClassDef]:
    return [node for node in ast.walk(ast.parse(file.content)) if isinstance(node, ast.ClassDef)]


def _decorator_name(decorator: ast.expr) -> str | None:
    if isinstance(decorator, ast.Name):
        return decorator.id
    if isinstance(decorator, ast.Attribute):
        return decorator.attr
    if isinstance(decorator, ast.Call):
        return _decorator_name(decorator.func)
    return None


def exceptions_reside_in_exception_package(file: FileInfo) -> bool:
    for node in _class_defs(file):
        if node.name.endswith("Error") and not _in_package(file, "exception"):
            return False
    return True


def dataclasses_reside_in_model_package(file: FileInfo) -> bool:
    for node in _class_defs(file):
        decorated = any(_decorator_name(item) == "dataclass" for item in node.decorator_list)
        if decorated and not _in_package(file, "model"):
            return False
    return True


def python_files_contain_no_ddl(file: FileInfo) -> bool:
    return _DDL.search(file.content) is None


def clients_reside_in_client_package(file: FileInfo) -> bool:
    for node in _class_defs(file):
        if node.name.endswith("Client") and not _in_package(file, "client"):
            return False
    return True


def test_exceptions_reside_in_exception_package() -> None:
    rule = (
        project_files(ROOT)
        .with_name("*.py")
        .should()
        .adhere_to(
            exceptions_reside_in_exception_package,
            "classes ending with Error reside in the exception package",
        )
    )
    assert_passes(rule)


def test_dataclasses_reside_in_model_package() -> None:
    rule = (
        project_files(ROOT)
        .with_name("*.py")
        .should()
        .adhere_to(
            dataclasses_reside_in_model_package,
            "classes marked with dataclass reside in the model package",
        )
    )
    assert_passes(rule)


def test_python_files_contain_no_ddl() -> None:
    rule = (
        project_files(ROOT)
        .with_name("*.py")
        .should()
        .adhere_to(
            python_files_contain_no_ddl,
            "schema changes live in SQL, not Python",
        )
    )
    assert_passes(rule)


def test_clients_reside_in_client_package() -> None:
    rule = (
        project_files(ROOT)
        .with_name("*.py")
        .should()
        .adhere_to(
            clients_reside_in_client_package,
            "classes ending with Client reside in the client package",
        )
    )
    assert_passes(rule)
