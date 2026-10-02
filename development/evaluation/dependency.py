"""Resolved AST import graph gate for checked-in Python source."""
import ast
from pathlib import Path


def audit_dependencies(checkout: Path):
    modules = {}
    for path in checkout.rglob('*.py'):
        relative = path.relative_to(checkout)
        if any(p.startswith('.') or p in ('tests', 'venv', '__pycache__') for p in relative.parts):
            continue
        module = '.'.join(relative.with_suffix('').parts)
        if module.endswith('.__init__'):
            module = module[:-9]
        modules[module] = path
    graph = {}
    failures = []
    for module, path in modules.items():
        edges = set()
        package = module if path.name == '__init__.py' else module.rpartition('.')[0]
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                edges.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    base = package.split('.')[:len(package.split('.'))-node.level+1]
                    target = '.'.join(base + ([node.module] if node.module else []))
                else:
                    target = node.module or ''
                edges.add(target)
                edges.update(target + '.' + alias.name for alias in node.names)
            elif isinstance(node, ast.Call):
                name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ''
                if name in ('import_module', '__import__'):
                    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                        edges.add(node.args[0].value)
                    elif module.startswith(('seed', 'development.evaluation.worker', 'development.evaluation.bootstrap')):
                        failures.append(module + ': unresolved dynamic import')
        # Retain unresolved targets too: an absent optional evaluator must not
        # make a prohibited import invisible to the dependency gate.
        graph[module] = edges | {e for edge in edges for e in [edge.rsplit('.', i)[0] for i in range(1, edge.count('.')+1)] if e in modules}
    for start in graph:
        if start.startswith('seed'):
            forbidden = ('development.evaluation',)
        elif start in ('development.evaluation.worker', 'development.evaluation.bootstrap', 'development.evaluation.channel'):
            forbidden = ('development.evaluation.scenarios', 'development.evaluation.coordinator', 'development.evaluation.analysis', 'development.evaluation.point_scores')
        elif start == 'development.evaluation.reader':
            forbidden = ('development.evaluation.coordinator', 'development.evaluation.worker', 'development.evaluation.scenarios', 'development.evaluation.point_scores')
        else:
            continue
        seen, pending = set(), [start]
        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)
            if current != start and current.startswith(forbidden):
                failures.append(start + ' -> ' + current)
            pending.extend(graph.get(current, ()))
    return tuple(sorted(set(failures)))
