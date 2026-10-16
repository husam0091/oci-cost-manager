import pytest
from scripts.check_response_leaks import check_sources


def test_security_scan_fails_on_missing_directories_and_secret_matches(tmp_path):
    root = tmp_path / 'backend'
    with pytest.raises(RuntimeError, match='directory missing'):
        check_sources(root)
    routes = root / 'api/routes'
    services = tmp_path / 'frontend/src/services'
    routes.mkdir(parents=True)
    services.mkdir(parents=True)
    (routes / 'safe.py').write_text('result = {"success": True}')
    (services / 'api.js').write_text('export const get = () => {};')
    check_sources(root)
    (routes / 'unsafe.py').write_text('response = {"oci_key_content": "test-value"}')
    with pytest.raises(RuntimeError, match='Sensitive response field') as exc:
        check_sources(root)
    assert 'test-value' not in str(exc.value)
