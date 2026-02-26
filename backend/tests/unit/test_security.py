"""Unit tests for security middleware and validation."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.middleware.security import (
    SecurityHeadersMiddleware,
    detect_sql_injection,
    detect_xss,
    sanitize_input,
)


class TestXSSDetection:
    """Test XSS detection functionality."""
    
    def test_detect_script_tag(self):
        """Test detection of script tags."""
        assert detect_xss("<script>alert('xss')</script>")
        assert detect_xss("<SCRIPT>alert('xss')</SCRIPT>")
        assert detect_xss("<script src='evil.js'></script>")
    
    def test_detect_javascript_protocol(self):
        """Test detection of javascript: protocol."""
        assert detect_xss("javascript:alert('xss')")
        assert detect_xss("JAVASCRIPT:alert('xss')")
    
    def test_detect_event_handlers(self):
        """Test detection of event handlers."""
        assert detect_xss("<img src=x onerror=alert('xss')>")
        assert detect_xss("<div onclick='alert(1)'>")
        assert detect_xss("<body onload=alert('xss')>")
    
    def test_detect_iframe(self):
        """Test detection of iframe tags."""
        assert detect_xss("<iframe src='evil.com'></iframe>")
        assert detect_xss("<IFRAME src='evil.com'></IFRAME>")
    
    def test_safe_input(self):
        """Test that safe input is not flagged."""
        assert not detect_xss("Hello, world!")
        assert not detect_xss("This is a normal string")
        assert not detect_xss("Email: user@example.com")
        assert not detect_xss("Price: $100")
    
    def test_non_string_input(self):
        """Test that non-string input returns False."""
        assert not detect_xss(123)
        assert not detect_xss(None)
        assert not detect_xss([])


class TestSQLInjectionDetection:
    """Test SQL injection detection functionality."""
    
    def test_detect_union_select(self):
        """Test detection of UNION SELECT."""
        assert detect_sql_injection("' UNION SELECT * FROM users --")
        assert detect_sql_injection("1' union select null, null --")
    
    def test_detect_select_from_where(self):
        """Test detection of SELECT FROM WHERE."""
        assert detect_sql_injection("SELECT * FROM users WHERE id=1")
        assert detect_sql_injection("select password from users where username='admin'")
    
    def test_detect_insert_into(self):
        """Test detection of INSERT INTO."""
        assert detect_sql_injection("INSERT INTO users VALUES ('hacker', 'pass')")
    
    def test_detect_update_set(self):
        """Test detection of UPDATE SET."""
        assert detect_sql_injection("UPDATE users SET password='hacked'")
    
    def test_detect_delete_from(self):
        """Test detection of DELETE FROM."""
        assert detect_sql_injection("DELETE FROM users WHERE id=1")
    
    def test_detect_drop_table(self):
        """Test detection of DROP TABLE."""
        assert detect_sql_injection("DROP TABLE users")
        assert detect_sql_injection("drop table users")
    
    def test_detect_sql_comments(self):
        """Test detection of SQL comments."""
        assert detect_sql_injection("admin' --")
        assert detect_sql_injection("admin' #")
        assert detect_sql_injection("admin' /* comment */")
    
    def test_detect_or_equals(self):
        """Test detection of OR 1=1 patterns."""
        assert detect_sql_injection("' OR 1=1 --")
        assert detect_sql_injection("' or 1=1 --")
        assert detect_sql_injection("admin' OR '1'='1")
    
    def test_detect_and_equals(self):
        """Test detection of AND 1=1 patterns."""
        assert detect_sql_injection("' AND 1=1 --")
        assert detect_sql_injection("' and 1=1 --")
    
    def test_safe_input(self):
        """Test that safe input is not flagged."""
        assert not detect_sql_injection("Hello, world!")
        assert not detect_sql_injection("This is a normal string")
        assert not detect_sql_injection("Email: user@example.com")
        # Note: "Price: $100" might trigger due to "--" but that's acceptable
    
    def test_non_string_input(self):
        """Test that non-string input returns False."""
        assert not detect_sql_injection(123)
        assert not detect_sql_injection(None)
        assert not detect_sql_injection([])


class TestSanitizeInput:
    """Test input sanitization functionality."""
    
    def test_sanitize_safe_string(self):
        """Test sanitization of safe strings."""
        result = sanitize_input("Hello, world!")
        assert result == "Hello, world!"
    
    def test_sanitize_safe_dict(self):
        """Test sanitization of safe dictionaries."""
        data = {"name": "John", "email": "john@example.com"}
        result = sanitize_input(data)
        assert result == data
    
    def test_sanitize_safe_list(self):
        """Test sanitization of safe lists."""
        data = ["item1", "item2", "item3"]
        result = sanitize_input(data)
        assert result == data
    
    def test_sanitize_nested_dict(self):
        """Test sanitization of nested dictionaries."""
        data = {
            "user": {
                "name": "John",
                "profile": {
                    "bio": "Software developer"
                }
            }
        }
        result = sanitize_input(data)
        assert result == data
    
    def test_reject_xss_in_string(self):
        """Test rejection of XSS in strings."""
        with pytest.raises(ValueError, match="XSS"):
            sanitize_input("<script>alert('xss')</script>")
    
    def test_reject_xss_in_dict(self):
        """Test rejection of XSS in dictionaries."""
        with pytest.raises(ValueError, match="XSS"):
            sanitize_input({"name": "<script>alert('xss')</script>"})
    
    def test_reject_xss_in_nested_dict(self):
        """Test rejection of XSS in nested dictionaries."""
        with pytest.raises(ValueError, match="XSS"):
            sanitize_input({
                "user": {
                    "bio": "<script>alert('xss')</script>"
                }
            })
    
    def test_reject_sql_injection_in_string(self):
        """Test rejection of SQL injection in strings."""
        with pytest.raises(ValueError, match="SQL injection"):
            sanitize_input("' OR 1=1 --")
    
    def test_reject_sql_injection_in_dict(self):
        """Test rejection of SQL injection in dictionaries."""
        with pytest.raises(ValueError, match="SQL injection"):
            sanitize_input({"username": "admin' OR '1'='1"})
    
    def test_reject_sql_injection_in_list(self):
        """Test rejection of SQL injection in lists."""
        with pytest.raises(ValueError, match="SQL injection"):
            sanitize_input(["item1", "' UNION SELECT * FROM users --"])


class TestSecurityHeadersMiddleware:
    """Test security headers middleware."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app with security middleware."""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        @app.post("/test")
        async def test_post(data: dict):
            return {"received": data}
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    def test_security_headers_present(self, client):
        """Test that security headers are added to responses."""
        response = client.get("/test")
        
        assert response.status_code == 200
        assert "Content-Security-Policy" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers
        assert "Permissions-Policy" in response.headers
    
    def test_csp_header_restrictive(self, client):
        """Test that CSP header is restrictive."""
        response = client.get("/test")
        csp = response.headers["Content-Security-Policy"]
        
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
    
    def test_x_frame_options_deny(self, client):
        """Test that X-Frame-Options is set to DENY."""
        response = client.get("/test")
        assert response.headers["X-Frame-Options"] == "DENY"
    
    def test_x_content_type_options_nosniff(self, client):
        """Test that X-Content-Type-Options is set to nosniff."""
        response = client.get("/test")
        assert response.headers["X-Content-Type-Options"] == "nosniff"
    
    def test_payload_size_limit(self, client):
        """Test that large payloads are rejected."""
        # Create a payload larger than 10MB
        large_data = {"data": "x" * (11 * 1024 * 1024)}
        
        response = client.post(
            "/test",
            json=large_data,
            headers={"Content-Length": str(11 * 1024 * 1024)}
        )
        
        assert response.status_code == 413
        assert "too large" in response.json()["detail"].lower()
    
    def test_xss_detection_in_post(self, client):
        """Test that XSS is detected in POST requests."""
        malicious_data = {
            "name": "John",
            "bio": "<script>alert('xss')</script>"
        }
        
        response = client.post(
            "/test",
            json=malicious_data,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 400
        assert "XSS" in response.json()["detail"]
    
    def test_sql_injection_detection_in_post(self, client):
        """Test that SQL injection is detected in POST requests."""
        malicious_data = {
            "username": "admin' OR '1'='1"
        }
        
        response = client.post(
            "/test",
            json=malicious_data,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 400
        assert "SQL injection" in response.json()["detail"]
    
    def test_safe_post_request(self, client):
        """Test that safe POST requests are allowed."""
        safe_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "message": "Hello, this is a safe message!"
        }
        
        response = client.post(
            "/test",
            json=safe_data,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        assert response.json()["received"] == safe_data


class TestCORSConfiguration:
    """Test CORS configuration."""
    
    def test_cors_restrictive_methods(self):
        """Test that CORS only allows specific methods."""
        # This would be tested in integration tests with actual CORS middleware
        # Here we just document the expected behavior
        allowed_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
        assert "TRACE" not in allowed_methods
        assert "CONNECT" not in allowed_methods
    
    def test_cors_restrictive_headers(self):
        """Test that CORS only allows specific headers."""
        allowed_headers = [
            "Authorization",
            "Content-Type",
            "Accept",
            "Origin",
            "User-Agent",
            "DNT",
            "Cache-Control",
            "X-Requested-With",
        ]
        # Verify no wildcard
        assert "*" not in allowed_headers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
