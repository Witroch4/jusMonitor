"""
Integration tests for webhook endpoint.

Tests:
- Signature validation
- Event routing
- Payload parsing
- Error handling
"""

import hashlib
import hmac
import json
from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


class TestWebhookEndpoint:
    """Test webhook endpoint functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def webhook_secret(self):
        """Webhook secret for signature generation."""
        return "test_webhook_secret_key"

    def generate_signature(self, payload: bytes, secret: str) -> str:
        """Generate HMAC signature for webhook payload."""
        return hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

    def test_chatwit_webhook_message_received(self, client, webhook_secret, monkeypatch):
        """Test receiving a message webhook from Chatwit."""
        # Set webhook secret
        monkeypatch.setenv("CHATWIT_WEBHOOK_SECRET", webhook_secret)

        # Create webhook payload
        payload = {
            "event_type": "message.received",
            "timestamp": datetime.utcnow().isoformat(),
            "contact": {
                "id": "contact_123",
                "name": "João Silva",
                "phone": "+5511999999999",
                "email": "joao@example.com",
                "tags": ["novo_lead"],
                "custom_fields": {},
            },
            "message": {
                "id": "msg_456",
                "direction": "inbound",
                "content": "Olá, preciso de ajuda com um processo",
                "media_url": None,
                "channel": "whatsapp",
            },
            "metadata": {},
        }

        # Generate signature
        payload_bytes = json.dumps(payload).encode()
        signature = self.generate_signature(payload_bytes, webhook_secret)

        # Send webhook request
        response = client.post(
            "/api/v1/webhooks/chatwit",
            json=payload,
            headers={"X-Chatwit-Signature": signature},
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
        assert "event_id" in data

    def test_chatwit_webhook_tag_added(self, client, webhook_secret, monkeypatch):
        """Test receiving a tag added webhook from Chatwit."""
        # Set webhook secret
        monkeypatch.setenv("CHATWIT_WEBHOOK_SECRET", webhook_secret)

        # Create webhook payload
        payload = {
            "event_type": "tag.added",
            "timestamp": datetime.utcnow().isoformat(),
            "contact": {
                "id": "contact_123",
                "name": "Maria Santos",
                "phone": "+5511888888888",
                "email": None,
                "tags": ["qualificado", "urgente"],
                "custom_fields": {},
            },
            "tag": "urgente",
            "metadata": {},
        }

        # Generate signature
        payload_bytes = json.dumps(payload).encode()
        signature = self.generate_signature(payload_bytes, webhook_secret)

        # Send webhook request
        response = client.post(
            "/api/v1/webhooks/chatwit",
            json=payload,
            headers={"X-Chatwit-Signature": signature},
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"

    def test_chatwit_webhook_tag_removed(self, client, webhook_secret, monkeypatch):
        """Test receiving a tag removed webhook from Chatwit."""
        # Set webhook secret
        monkeypatch.setenv("CHATWIT_WEBHOOK_SECRET", webhook_secret)

        # Create webhook payload
        payload = {
            "event_type": "tag.removed",
            "timestamp": datetime.utcnow().isoformat(),
            "contact": {
                "id": "contact_123",
                "name": "Pedro Oliveira",
                "phone": "+5511777777777",
                "email": "pedro@example.com",
                "tags": ["qualificado"],
                "custom_fields": {},
            },
            "tag": "novo_lead",
            "metadata": {},
        }

        # Generate signature
        payload_bytes = json.dumps(payload).encode()
        signature = self.generate_signature(payload_bytes, webhook_secret)

        # Send webhook request
        response = client.post(
            "/api/v1/webhooks/chatwit",
            json=payload,
            headers={"X-Chatwit-Signature": signature},
        )

        # Verify response
        assert response.status_code == 200

    def test_chatwit_webhook_invalid_signature(self, client, webhook_secret, monkeypatch):
        """Test webhook with invalid signature is rejected."""
        # Set webhook secret
        monkeypatch.setenv("CHATWIT_WEBHOOK_SECRET", webhook_secret)

        # Create webhook payload
        payload = {
            "event_type": "message.received",
            "timestamp": datetime.utcnow().isoformat(),
            "contact": {
                "id": "contact_123",
                "name": "Test User",
                "phone": "+5511999999999",
                "email": None,
                "tags": [],
                "custom_fields": {},
            },
            "message": {
                "id": "msg_789",
                "direction": "inbound",
                "content": "Test message",
                "media_url": None,
                "channel": "whatsapp",
            },
            "metadata": {},
        }

        # Use invalid signature
        invalid_signature = "invalid_signature_12345"

        # Send webhook request
        response = client.post(
            "/api/v1/webhooks/chatwit",
            json=payload,
            headers={"X-Chatwit-Signature": invalid_signature},
        )

        # Should be rejected
        assert response.status_code == 401
        assert "Invalid webhook signature" in response.json()["detail"]

    def test_chatwit_webhook_missing_signature(self, client, monkeypatch):
        """Test webhook without signature header."""
        # Set webhook secret
        monkeypatch.setenv("CHATWIT_WEBHOOK_SECRET", "some_secret")

        # Create webhook payload
        payload = {
            "event_type": "message.received",
            "timestamp": datetime.utcnow().isoformat(),
            "contact": {
                "id": "contact_123",
                "name": "Test User",
                "phone": "+5511999999999",
                "email": None,
                "tags": [],
                "custom_fields": {},
            },
            "message": {
                "id": "msg_789",
                "direction": "inbound",
                "content": "Test message",
                "media_url": None,
                "channel": "whatsapp",
            },
            "metadata": {},
        }

        # Send webhook request without signature
        response = client.post(
            "/api/v1/webhooks/chatwit",
            json=payload,
        )

        # Should still accept (logs warning) in development
        # In production, this should be rejected
        assert response.status_code in [200, 401]

    def test_chatwit_webhook_invalid_payload(self, client, webhook_secret, monkeypatch):
        """Test webhook with invalid payload structure."""
        # Set webhook secret
        monkeypatch.setenv("CHATWIT_WEBHOOK_SECRET", webhook_secret)

        # Create invalid payload (missing required fields)
        payload = {
            "event_type": "message.received",
            # Missing timestamp, contact, message
        }

        # Generate signature
        payload_bytes = json.dumps(payload).encode()
        signature = self.generate_signature(payload_bytes, webhook_secret)

        # Send webhook request
        response = client.post(
            "/api/v1/webhooks/chatwit",
            json=payload,
            headers={"X-Chatwit-Signature": signature},
        )

        # Should return 400 Bad Request
        assert response.status_code == 400
        assert "Invalid webhook payload" in response.json()["detail"]

    def test_chatwit_webhook_malformed_json(self, client):
        """Test webhook with malformed JSON."""
        # Send malformed JSON
        response = client.post(
            "/api/v1/webhooks/chatwit",
            data="not valid json {{{",
            headers={"Content-Type": "application/json"},
        )

        # Should return 422 Unprocessable Entity
        assert response.status_code == 422

    def test_chatwit_webhook_response_time(self, client, webhook_secret, monkeypatch):
        """Test that webhook responds quickly (< 5 seconds)."""
        import time

        # Set webhook secret
        monkeypatch.setenv("CHATWIT_WEBHOOK_SECRET", webhook_secret)

        # Create webhook payload
        payload = {
            "event_type": "message.received",
            "timestamp": datetime.utcnow().isoformat(),
            "contact": {
                "id": "contact_123",
                "name": "Speed Test",
                "phone": "+5511999999999",
                "email": None,
                "tags": [],
                "custom_fields": {},
            },
            "message": {
                "id": "msg_speed",
                "direction": "inbound",
                "content": "Testing response time",
                "media_url": None,
                "channel": "whatsapp",
            },
            "metadata": {},
        }

        # Generate signature
        payload_bytes = json.dumps(payload).encode()
        signature = self.generate_signature(payload_bytes, webhook_secret)

        # Measure response time
        start = time.time()
        response = client.post(
            "/api/v1/webhooks/chatwit",
            json=payload,
            headers={"X-Chatwit-Signature": signature},
        )
        duration = time.time() - start

        # Should respond quickly
        assert response.status_code == 200
        assert duration < 5.0  # Must respond within 5 seconds

    def test_chatwit_webhook_with_media(self, client, webhook_secret, monkeypatch):
        """Test webhook with media attachment."""
        # Set webhook secret
        monkeypatch.setenv("CHATWIT_WEBHOOK_SECRET", webhook_secret)

        # Create webhook payload with media
        payload = {
            "event_type": "message.received",
            "timestamp": datetime.utcnow().isoformat(),
            "contact": {
                "id": "contact_123",
                "name": "Media Sender",
                "phone": "+5511999999999",
                "email": None,
                "tags": [],
                "custom_fields": {},
            },
            "message": {
                "id": "msg_media",
                "direction": "inbound",
                "content": "Segue documento anexo",
                "media_url": "https://example.com/media/document.pdf",
                "channel": "whatsapp",
            },
            "metadata": {},
        }

        # Generate signature
        payload_bytes = json.dumps(payload).encode()
        signature = self.generate_signature(payload_bytes, webhook_secret)

        # Send webhook request
        response = client.post(
            "/api/v1/webhooks/chatwit",
            json=payload,
            headers={"X-Chatwit-Signature": signature},
        )

        # Verify response
        assert response.status_code == 200

    def test_chatwit_webhook_multiple_tags(self, client, webhook_secret, monkeypatch):
        """Test webhook with contact having multiple tags."""
        # Set webhook secret
        monkeypatch.setenv("CHATWIT_WEBHOOK_SECRET", webhook_secret)

        # Create webhook payload
        payload = {
            "event_type": "message.received",
            "timestamp": datetime.utcnow().isoformat(),
            "contact": {
                "id": "contact_multi_tag",
                "name": "Multi Tag User",
                "phone": "+5511999999999",
                "email": "multi@example.com",
                "tags": ["novo_lead", "qualificado", "urgente", "vip"],
                "custom_fields": {"source": "website", "campaign": "google_ads"},
            },
            "message": {
                "id": "msg_multi",
                "direction": "inbound",
                "content": "Mensagem de teste",
                "media_url": None,
                "channel": "whatsapp",
            },
            "metadata": {},
        }

        # Generate signature
        payload_bytes = json.dumps(payload).encode()
        signature = self.generate_signature(payload_bytes, webhook_secret)

        # Send webhook request
        response = client.post(
            "/api/v1/webhooks/chatwit",
            json=payload,
            headers={"X-Chatwit-Signature": signature},
        )

        # Verify response
        assert response.status_code == 200

    def test_chatwit_webhook_different_channels(self, client, webhook_secret, monkeypatch):
        """Test webhooks from different channels."""
        # Set webhook secret
        monkeypatch.setenv("CHATWIT_WEBHOOK_SECRET", webhook_secret)

        channels = ["whatsapp", "instagram", "telegram", "webchat"]

        for channel in channels:
            payload = {
                "event_type": "message.received",
                "timestamp": datetime.utcnow().isoformat(),
                "contact": {
                    "id": f"contact_{channel}",
                    "name": f"User from {channel}",
                    "phone": "+5511999999999",
                    "email": None,
                    "tags": [],
                    "custom_fields": {},
                },
                "message": {
                    "id": f"msg_{channel}",
                    "direction": "inbound",
                    "content": f"Message from {channel}",
                    "media_url": None,
                    "channel": channel,
                },
                "metadata": {},
            }

            # Generate signature
            payload_bytes = json.dumps(payload).encode()
            signature = self.generate_signature(payload_bytes, webhook_secret)

            # Send webhook request
            response = client.post(
                "/api/v1/webhooks/chatwit",
                json=payload,
                headers={"X-Chatwit-Signature": signature},
            )

            # Verify response
            assert response.status_code == 200, f"Failed for channel: {channel}"
