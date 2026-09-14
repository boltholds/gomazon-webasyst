from __future__ import annotations

import ast
from pathlib import Path


ROOTS = (
    Path('src/gomazon_webasyst/application'),
    Path('src/gomazon_webasyst/compatibility/webasyst/dispatch'),
    Path('src/gomazon_webasyst/compatibility/webasyst/routing'),
    Path('src/gomazon_webasyst/infrastructure/auth'),
    Path('src/gomazon_webasyst/infrastructure/sessions'),
)
EXCLUDED = {
    Path('src/gomazon_webasyst/compatibility/webasyst/routing/legacy_parser.py'),
}


def _annotation_is_optional_result(annotation: ast.expr | None) -> bool:
    if annotation is None:
        return False
    text = ast.unparse(annotation)
    return '| None' in text or text.startswith('Optional[')


def test_operation_and_lookup_contracts_do_not_return_optional_sentinels():
    violations: list[str] = []
    for root in ROOTS:
        for path in root.rglob('*.py'):
            if path in EXCLUDED:
                continue
            tree = ast.parse(path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if _annotation_is_optional_result(node.returns):
                        violations.append(f'{path}:{node.lineno}:{node.name}')
    assert violations == [], 'Optional result contracts found:\n' + '\n'.join(violations)


def test_none_union_annotations_are_limited_to_true_nullable_boundaries():
    nullable_orm = Path('src/gomazon_webasyst/infrastructure/persistence/sqlalchemy/models.py')
    violations: list[str] = []

    for path in Path('src/gomazon_webasyst').rglob('*.py'):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.AnnAssign) and _annotation_is_optional_result(node.annotation):
                if path != nullable_orm:
                    violations.append(f'{path}:{node.lineno}:annotated-value')
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                all_args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
                for arg in all_args:
                    if not _annotation_is_optional_result(arg.annotation):
                        continue
                    if node.name == '__aexit__':
                        continue
                    violations.append(f'{path}:{node.lineno}:{node.name}({arg.arg})')
                if _annotation_is_optional_result(node.returns):
                    violations.append(f'{path}:{node.lineno}:{node.name}->return')

    assert violations == [], 'Unexpected Optional/None annotations:\n' + '\n'.join(violations)
