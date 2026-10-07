from pathlib import Path

from app.security.auth import hash_password, verify_password


def test_argon2_password_roundtrip():
    password = 'Strong-Password-123!'
    stored = hash_password(password)
    assert stored.startswith('$argon2')
    assert verify_password(password, stored)
    assert not verify_password('wrong-password', stored)


def test_requirements_do_not_depend_on_passlib():
    requirements = Path('requirements.txt').read_text().lower()
    assert 'passlib' not in requirements
    assert 'argon2-cffi' in requirements
