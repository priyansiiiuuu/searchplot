import sys
import os
import pytest
from fastapi import HTTPException

# Configure sys.path to locate the backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from crawler.crawler import (
    normalize_url,
    is_crawlable_url,
    get_hostname,
    is_safe_ip,
    is_safe_url,
    crawl_site
)
from main import validate_url


def test_url_normalization():
    # Defragmentation check
    assert normalize_url("https://example.com/about#team") == "https://example.com/about"
    # Case insensitivity checks
    assert normalize_url("HTTPS://EXAMPLE.COM/Page") == "https://example.com/Page"
    # Trailing slash pruning check
    assert normalize_url("https://example.com/blog/") == "https://example.com/blog"
    # Root paths preserve trailing slash
    assert normalize_url("https://example.com/") == "https://example.com/"


def test_host_classification():
    assert get_hostname("https://example.com/sub/page") == "example.com"
    assert get_hostname("http://sub.domain.co.uk/test") == "sub.domain.co.uk"


def test_blocked_paths_and_extensions():
    # PDF document extension block check
    assert not is_crawlable_url("https://example.com/files/report.pdf", "example.com")
    # Image extension block check
    assert not is_crawlable_url("https://example.com/static/hero.png", "example.com")
    # MediaWiki special path pattern block check
    assert not is_crawlable_url("https://example.com/special:login", "example.com")
    
    # Valid crawlable page checks
    assert is_crawlable_url("https://example.com/products", "example.com")
    assert is_crawlable_url("https://example.com/about-us", "example.com")
    # Hostname mismatch check
    assert not is_crawlable_url("https://other-domain.com/about", "example.com")


def test_ssrf_and_private_ip_blocking():
    # Loopback addresses
    assert not is_safe_ip("127.0.0.1")
    assert not is_safe_ip("::1")
    assert not is_safe_ip("0.0.0.0")
    
    # Private IP ranges
    assert not is_safe_ip("10.0.0.1")
    assert not is_safe_ip("172.16.4.15")
    assert not is_safe_ip("192.168.1.100")
    
    # Link local / Cloud metadata
    assert not is_safe_ip("169.254.169.254")
    assert not is_safe_ip("fe80::254")
    
    # Valid public IPs
    assert is_safe_ip("8.8.8.8")
    assert is_safe_ip("1.1.1.1")
    assert is_safe_ip("142.250.190.46")

    # API validate_url validation error checks
    with pytest.raises(HTTPException) as exc_info_loopback:
        validate_url("http://127.0.0.1:8000")
    assert exc_info_loopback.value.status_code == 400

    with pytest.raises(HTTPException) as exc_info_metadata:
        validate_url("http://169.254.169.254/latest/meta-data/")
    assert exc_info_metadata.value.status_code == 400


def test_basic_crawl_failure_handling():
    # Test that crawl_site handles a nonexistent domain cleanly and returns the failure details
    results = crawl_site("https://nonexistentdomain123.com", max_pages=1)
    
    assert len(results) == 1
    assert results[0]["url"] == "https://nonexistentdomain123.com/"
    assert results[0]["status_code"] == 0
    assert "error" in results[0]
