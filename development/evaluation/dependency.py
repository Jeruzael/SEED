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
        unresolved=False
        package = module if path.name == '__init__.py' else module.rpartition('.')[0]
        tree=ast.parse(path.read_text())
        bindings={'__import__':'builtins.__import__'}
        nodes=list(ast.walk(tree))
        for node in nodes:
            if isinstance(node,ast.Import):
                for alias in node.names: bindings[alias.asname or alias.name.split('.')[0]]=alias.name if alias.asname else alias.name.split('.')[0]
            elif isinstance(node,ast.ImportFrom) and node.module in ('importlib','builtins'):
                for alias in node.names: bindings[alias.asname or alias.name]=node.module+'.'+alias.name
        def resolved(node):
            if isinstance(node,ast.Name): return bindings.get(node.id,node.id)
            if isinstance(node,ast.Attribute): return resolved(node.value)+'.'+node.attr
            return ''
        # Fixed-point assignment aliases, including functions exported through a local name.
        for _ in range(len(nodes)+1):
            changed=False
            for node in nodes:
                if isinstance(node,ast.Assign):
                    value=resolved(node.value)
                    if value in ('importlib','builtins','importlib.import_module','builtins.__import__'):
                        for target in node.targets:
                            if isinstance(target,ast.Name) and bindings.get(target.id)!=value:
                                bindings[target.id]=value; changed=True
            if not changed: break
        for node in nodes:
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
                name=resolved(node.func)
                if name in ('importlib.import_module','builtins.__import__'):
                    if node.args and isinstance(node.args[0],ast.Constant) and isinstance(node.args[0].value,str) and not node.args[0].value.startswith('.'):
                        edges.add(node.args[0].value)
                    else:
                        unresolved=True
        if unresolved:
            edges.add('<unresolved dynamic import>')
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
            if current=='<unresolved dynamic import>':
                failures.append(start+': unresolved reachable dynamic import')
            if current != start and current.startswith(forbidden):
                failures.append(start + ' -> ' + current)
            pending.extend(graph.get(current, ()))
    return tuple(sorted(set(failures)))
