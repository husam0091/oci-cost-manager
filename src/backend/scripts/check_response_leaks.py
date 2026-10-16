"""Fail closed on sensitive response fields or key material in API source."""
import re
from pathlib import Path


def check_sources(root: Path) -> None:
    checks = [
        (r'"(oci_key_content|oci_key_file|oci_pass_phrase|oci_config_file)"\s*:', [root / 'api/routes']),
        (r'-----BEGIN|PRIVATE KEY', [root / 'api/routes', root.parent / 'frontend/src/services']),
    ]
    matches = []
    for pattern, directories in checks:
        for directory in directories:
            if not directory.is_dir():
                raise RuntimeError(f'Security scan directory missing: {directory}')
            paths = sorted(p for p in directory.rglob('*') if p.is_file() and p.suffix in {'.py', '.js', '.jsx'})
            if not paths:
                raise RuntimeError(f'Security scan found no source files: {directory}')
            for path in paths:
                for line_number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                    if re.search(pattern, line):
                        # Never echo the matching line: it could contain a secret.
                        matches.append(f'{path}:{line_number}')
    if matches:
        raise RuntimeError('Sensitive response field or key material detected at: ' + ', '.join(matches))


if __name__ == '__main__':
    check_sources(Path(__file__).resolve().parents[1])
    print('Security response leak checks passed')
