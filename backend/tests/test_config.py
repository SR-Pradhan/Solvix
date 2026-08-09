from app.core.config import Settings


def _settings(monkeypatch, value=None):
    if value is None:
        monkeypatch.delenv("CORS_ORIGINS", raising=False)
    else:
        monkeypatch.setenv("CORS_ORIGINS", value)
    return Settings()


def test_cors_origins_accepts_comma_separated(monkeypatch):
    # The form a hosting dashboard makes you type.
    s = _settings(monkeypatch, "https://solvix.vercel.app,http://localhost:5173")
    assert s.cors_origins == ["https://solvix.vercel.app", "http://localhost:5173"]


def test_cors_origins_ignores_surrounding_whitespace(monkeypatch):
    s = _settings(monkeypatch, " https://a.app ,  https://b.app , ")
    assert s.cors_origins == ["https://a.app", "https://b.app"]


def test_cors_origins_still_accepts_json(monkeypatch):
    # The original format, so existing .env files keep working.
    s = _settings(monkeypatch, '["https://a.app", "https://b.app"]')
    assert s.cors_origins == ["https://a.app", "https://b.app"]


def test_cors_origins_defaults_to_local_dev(monkeypatch):
    s = _settings(monkeypatch)
    assert s.cors_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]
