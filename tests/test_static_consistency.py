# Static (AST) checks of the layers that need SQLAlchemy / Flask / Marshmallow at runtime.
# They catch the classic wiring mistakes (typo in a column, missing repository method, wrong DI argument,
# controller calling a service method that does not exist) even on a machine without those libraries.

import ast
import importlib
import inspect
import pkgutil
from dataclasses import fields, is_dataclass
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"


def parse(path):
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def py_files(*parts):
    return sorted(p for p in SRC.joinpath(*parts).rglob("*.py") if p.name != "__init__.py")


def import_all(package):
    """Import every module of a pure-python package (domain, services) and return {class_name: class}."""
    found = {}
    pkg = importlib.import_module(package)
    for info in pkgutil.walk_packages(pkg.__path__, package + "."):
        module = importlib.import_module(info.name)
        for name, obj in vars(module).items():
            if inspect.isclass(obj) and obj.__module__ == module.__name__:
                found[name] = obj
    return found


def test_every_python_file_compiles():
    for path in list(SRC.rglob("*.py")) + list((SRC.parent / "simulator").rglob("*.py")):
        compile(path.read_text(encoding="utf-8"), str(path), "exec")


def test_repositories_implement_every_interface_method():
    interfaces = import_all("domain.models")
    problems = []
    for path in py_files("infrastructure", "repositories"):
        for node in [n for n in parse(path).body if isinstance(n, ast.ClassDef)]:
            defined = {f.name for f in node.body if isinstance(f, ast.FunctionDef)}
            for base in node.bases:
                iface = interfaces.get(getattr(base, "id", ""))
                if iface is not None and getattr(iface, "__abstractmethods__", None):
                    missing = set(iface.__abstractmethods__) - defined
                    if missing:
                        problems.append(f"{path.name}:{node.name} misses {sorted(missing)}")
    assert not problems, problems


def _model_columns():
    """{ModelClass: set(attribute names)} from infrastructure/models/*.py (mixins included)."""
    columns = {}
    for path in py_files("infrastructure", "models"):
        for node in [n for n in parse(path).body if isinstance(n, ast.ClassDef)]:
            names = {t.id for stmt in node.body if isinstance(stmt, ast.Assign) for t in stmt.targets
                     if isinstance(t, ast.Name)}
            bases = {getattr(b, "id", "") for b in node.bases}
            if "IdMixin" in bases:
                names.add("id")
            if "TimestampMixin" in bases:
                names |= {"created_at", "updated_at"}
            columns[node.name] = names
    return columns


def test_entity_fields_exist_as_orm_columns():
    entities = {k: v for k, v in import_all("domain.models").items() if is_dataclass(v)}
    columns = _model_columns()
    pairs = {("BottleModel", "Bottle"), ("InventoryBatchModel", "InventoryBatch"),
             ("InventoryLogModel", "InventoryLog"), ("OrderStatusHistoryModel", "OrderStatusHistory"),
             ("PaymentWebhookEventModel", "WebhookEvent")}
    for path in py_files("infrastructure", "repositories"):              # model, entity = XModel, Entity
        for node in ast.walk(parse(path)):
            if (isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Tuple)
                    and [getattr(t, "id", "") for t in node.targets[0].elts] == ["model", "entity"]):
                pairs.add(tuple(e.id for e in node.value.elts))
    assert len(pairs) >= 20, pairs
    problems = []
    for model_name, entity_name in sorted(pairs):
        assert model_name in columns, f"{model_name} not found"
        missing = {f.name for f in fields(entities[entity_name])} - columns[model_name]
        if missing:
            problems.append(f"{entity_name} has fields {sorted(missing)} not present in {model_name}")
    assert not problems, problems


def test_erd_has_29_tables_and_every_model_is_imported():
    tables = []
    for path in py_files("infrastructure", "models"):
        for node in ast.walk(parse(path)):
            if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "__tablename__":
                tables.append(node.value.value)
    assert len(tables) == len(set(tables)) == 29, sorted(tables)
    init = (SRC / "infrastructure" / "models" / "__init__.py").read_text()
    model_classes = [c for c in _model_columns() if c.endswith("Model")]
    assert all(name in init for name in model_classes), [n for n in model_classes if n not in init]


def _container_providers():
    """{provider_name: (ClassName, [kwarg names])} from dependency_container.py"""
    result = {}
    for node in ast.walk(parse(SRC / "dependency_container.py")):
        if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
                and getattr(node.value.func, "attr", "") in ("Factory", "Singleton") and node.value.args):
            result[node.targets[0].id] = (node.value.args[0].id, [k.arg for k in node.value.keywords])
    return result


def test_container_passes_the_right_arguments_to_services():
    services = import_all("services")
    problems = []
    for name, (cls_name, kwargs) in _container_providers().items():
        cls = services.get(cls_name)
        if cls is None:
            continue                                                      # infrastructure class
        params = inspect.signature(cls.__init__).parameters
        unknown = set(kwargs) - set(params)
        required = {p for p, v in params.items() if p != "self" and v.default is inspect.Parameter.empty} - set(kwargs)
        if unknown or required:
            problems.append(f"{name}: unknown={sorted(unknown)} missing={sorted(required)}")
    assert not problems, problems


def test_controllers_only_call_existing_service_methods():
    providers = _container_providers()
    services = import_all("services")
    interfaces = import_all("domain.models")
    checked, problems = 0, []
    for path in py_files("api", "controllers"):
        for node in ast.walk(parse(path)):
            # container.<provider>().<method>(...)
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Call) and isinstance(node.func.value.func, ast.Attribute)
                    and getattr(node.func.value.func.value, "id", "") == "container"):
                provider, method = node.func.value.func.attr, node.func.attr
                assert provider in providers, f"{path.name}: unknown provider {provider}"
                cls = services.get(providers[provider][0])
                if cls is not None:
                    checked += 1
                    if not hasattr(cls, method):
                        problems.append(f"{path.name}: {cls.__name__}.{method} does not exist")
    assert checked > 30 and not problems, problems


def test_every_route_function_has_a_docstring_for_swagger():
    for path in py_files("api", "controllers"):
        for node in ast.walk(parse(path)):
            if isinstance(node, ast.FunctionDef) and any(
                    isinstance(d, ast.Call) and getattr(d.func, "attr", "") == "route" for d in node.decorator_list):
                assert ast.get_docstring(node), f"{path.name}:{node.name} has no docstring"
