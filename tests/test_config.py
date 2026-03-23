from src.config import ServerConfig

def test_default_config():
    config = ServerConfig()
    assert config.host == "127.0.0.1"
    assert config.port == 8765
    assert config.endpoint == "/mcp"

def test_env_override(monkeypatch):
    monkeypatch.setenv("MCP_PORT", "9999")
    config = ServerConfig()
    assert config.port == 9999
