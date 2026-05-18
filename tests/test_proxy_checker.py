import pytest

from app.models.account import ProxyConfig
from app.services.proxy.checker import ProxyChecker


@pytest.mark.asyncio
async def test_build_proxy_url_with_auth() -> None:
    proxy = ProxyConfig(host="1.2.3.4", port=8080, username="user", password="pass")
    url = ProxyChecker._build_proxy_url(proxy)
    assert url == "http://user:pass@1.2.3.4:8080"
