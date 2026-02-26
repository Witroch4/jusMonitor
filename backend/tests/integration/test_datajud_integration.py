"""
Integration tests for DataJud client.

Tests:
- Rate limiting (1 req/36s)
- search_cases functionality
- get_movements functionality
- Retry logic with exponential backoff
- Batching system
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest

from app.core.services.datajud.batcher import Batch, DataJudBatcher
from app.core.services.datajud.client import (
    DataJudClient,
    DataJudRateLimitError,
)


class TestDataJudClient:
    """Test DataJud client functionality."""

    @pytest.fixture
    def mock_httpx_client(self):
        """Create a mock httpx client."""
        with patch("app.core.services.datajud.client.httpx.AsyncClient") as mock:
            client_instance = AsyncMock()
            mock.return_value = client_instance
            yield client_instance

    @pytest.fixture
    def datajud_client(self, mock_httpx_client):
        """Create a DataJud client with mocked HTTP."""
        return DataJudClient(
            base_url="https://api.datajud.test",
            cert_path=None,  # Skip cert for testing
            key_path=None,
            timeout=30.0,
        )

    @pytest.mark.asyncio
    async def test_rate_limiting_enforced(self, datajud_client, mock_httpx_client):
        """Test that rate limiting (1 req/36s) is enforced."""
        # Mock successful responses
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"processos": []}
        mock_httpx_client.request.return_value = mock_response

        # Set shorter interval for testing
        datajud_client.min_interval = 1.0

        # First request should be immediate
        start = datetime.utcnow()
        await datajud_client.search_cases(cnj_numbers=["0000001-00.0000.0.00.0000"])
        first_duration = (datetime.utcnow() - start).total_seconds()
        assert first_duration < 0.2

        # Second request should wait ~1 second
        start = datetime.utcnow()
        await datajud_client.search_cases(cnj_numbers=["0000002-00.0000.0.00.0000"])
        second_duration = (datetime.utcnow() - start).total_seconds()
        assert 0.8 <= second_duration <= 1.5

    @pytest.mark.asyncio
    async def test_search_cases_success(self, datajud_client, mock_httpx_client):
        """Test successful case search."""
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "processos": [
                {
                    "numeroCnj": "0000001-00.2023.8.00.0000",
                    "tribunal": "TJSP",
                    "assunto": "Ação Civil",
                },
                {
                    "numeroCnj": "0000002-00.2023.8.00.0000",
                    "tribunal": "TJRJ",
                    "assunto": "Ação Penal",
                },
            ]
        }
        mock_httpx_client.request.return_value = mock_response

        # Search cases
        result = await datajud_client.search_cases(
            cnj_numbers=["0000001-00.2023.8.00.0000", "0000002-00.2023.8.00.0000"]
        )

        # Verify result
        assert len(result) == 2
        assert "0000001-00.2023.8.00.0000" in result
        assert result["0000001-00.2023.8.00.0000"]["tribunal"] == "TJSP"

        # Verify request
        mock_httpx_client.request.assert_called_once()
        call_args = mock_httpx_client.request.call_args
        assert call_args[0][0] == "POST"
        assert "/processos/consulta" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_get_movements_success(self, datajud_client, mock_httpx_client):
        """Test successful movements retrieval."""
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "processos": [
                {
                    "numeroCnj": "0000001-00.2023.8.00.0000",
                    "movimentacoes": [
                        {
                            "data": "2023-12-01",
                            "tipo": "Sentença",
                            "descricao": "Sentença proferida",
                        },
                        {
                            "data": "2023-12-15",
                            "tipo": "Publicação",
                            "descricao": "Publicação no DJE",
                        },
                    ],
                }
            ]
        }
        mock_httpx_client.request.return_value = mock_response

        # Get movements
        result = await datajud_client.get_movements(
            cnj_numbers=["0000001-00.2023.8.00.0000"]
        )

        # Verify result
        assert len(result) == 1
        assert "0000001-00.2023.8.00.0000" in result
        assert len(result["0000001-00.2023.8.00.0000"]) == 2
        assert result["0000001-00.2023.8.00.0000"][0]["tipo"] == "Sentença"

    @pytest.mark.asyncio
    async def test_get_movements_max_100_limit(self, datajud_client):
        """Test that get_movements enforces max 100 CNJ numbers."""
        # Create 101 CNJ numbers
        cnj_numbers = [f"000000{i:04d}-00.2023.8.00.0000" for i in range(101)]

        # Should raise ValueError
        with pytest.raises(ValueError, match="Maximum 100 CNJ numbers"):
            await datajud_client.get_movements(cnj_numbers=cnj_numbers)

    @pytest.mark.asyncio
    async def test_rate_limit_429_handling(self, datajud_client, mock_httpx_client):
        """Test handling of 429 rate limit errors."""
        # Mock 429 response
        mock_response = AsyncMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_httpx_client.request.return_value = mock_response

        # Should raise DataJudRateLimitError
        with pytest.raises(DataJudRateLimitError):
            await datajud_client.search_cases(cnj_numbers=["0000001-00.2023.8.00.0000"])

    @pytest.mark.asyncio
    async def test_retry_on_http_error(self, datajud_client, mock_httpx_client):
        """Test retry logic with exponential backoff."""
        # Mock responses: fail twice, then succeed
        mock_response_fail = AsyncMock()
        mock_response_fail.status_code = 500
        mock_response_fail.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error",
            request=AsyncMock(),
            response=mock_response_fail,
        )

        mock_response_success = AsyncMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"processos": []}

        # First 2 calls fail, 3rd succeeds
        mock_httpx_client.request.side_effect = [
            mock_response_fail,
            mock_response_fail,
            mock_response_success,
        ]

        # Should eventually succeed after retries
        result = await datajud_client.search_cases(cnj_numbers=["0000001-00.2023.8.00.0000"])

        # Verify it retried 3 times
        assert mock_httpx_client.request.call_count == 3

    @pytest.mark.asyncio
    async def test_timeout_handling(self, datajud_client, mock_httpx_client):
        """Test handling of timeouts."""
        # Mock timeout
        mock_httpx_client.request.side_effect = httpx.TimeoutException("Timeout")

        # Should raise TimeoutException after retries
        with pytest.raises(httpx.TimeoutException):
            await datajud_client.search_cases(cnj_numbers=["0000001-00.2023.8.00.0000"])

        # Verify it retried 3 times
        assert mock_httpx_client.request.call_count == 3

    @pytest.mark.asyncio
    async def test_get_case_details(self, datajud_client, mock_httpx_client):
        """Test getting detailed case information."""
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "numeroCnj": "0000001-00.2023.8.00.0000",
            "tribunal": "TJSP",
            "partes": [
                {"tipo": "Autor", "nome": "João Silva"},
                {"tipo": "Réu", "nome": "Maria Santos"},
            ],
            "movimentacoes": [],
        }
        mock_httpx_client.request.return_value = mock_response

        # Get case details
        result = await datajud_client.get_case_details("0000001-00.2023.8.00.0000")

        # Verify result
        assert result["numeroCnj"] == "0000001-00.2023.8.00.0000"
        assert len(result["partes"]) == 2

        # Verify GET request was made
        call_args = mock_httpx_client.request.call_args
        assert call_args[0][0] == "GET"
        assert "0000001-00.2023.8.00.0000" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_httpx_client):
        """Test client as async context manager."""
        async with DataJudClient(
            base_url="https://api.datajud.test",
            cert_path=None,
            key_path=None,
        ) as client:
            assert client is not None

        # Verify client was closed
        mock_httpx_client.aclose.assert_called_once()


class TestDataJudBatcher:
    """Test DataJud batching system."""

    @pytest.fixture
    def batcher(self):
        """Create a batcher instance."""
        return DataJudBatcher(
            batch_size=100,
            delay_seconds=36.0,
            distribution_hours=6,
        )

    def test_create_batches_single_batch(self, batcher):
        """Test creating batches with less than 100 processes."""
        cnj_numbers = [f"000000{i:02d}-00.2023.8.00.0000" for i in range(50)]
        tenant_id = uuid4()

        batches = batcher.create_batches(cnj_numbers, tenant_id)

        # Should create 1 batch
        assert len(batches) == 1
        assert len(batches[0].cnj_numbers) == 50
        assert batches[0].tenant_id == tenant_id

    def test_create_batches_multiple_batches(self, batcher):
        """Test creating batches with more than 100 processes."""
        cnj_numbers = [f"000000{i:03d}-00.2023.8.00.0000" for i in range(250)]
        tenant_id = uuid4()

        batches = batcher.create_batches(cnj_numbers, tenant_id)

        # Should create 3 batches (100, 100, 50)
        assert len(batches) == 3
        assert len(batches[0].cnj_numbers) == 100
        assert len(batches[1].cnj_numbers) == 100
        assert len(batches[2].cnj_numbers) == 50

    def test_batch_scheduling_delays(self, batcher):
        """Test that batches are scheduled with correct delays."""
        cnj_numbers = [f"000000{i:03d}-00.2023.8.00.0000" for i in range(300)]
        tenant_id = uuid4()
        start_time = datetime.utcnow()

        batches = batcher.create_batches(cnj_numbers, tenant_id, start_time)

        # Verify delays between batches
        assert batches[0].scheduled_at == start_time
        assert batches[1].scheduled_at == start_time + timedelta(seconds=36)
        assert batches[2].scheduled_at == start_time + timedelta(seconds=72)

    def test_calculate_distribution(self, batcher):
        """Test distribution calculation."""
        stats = batcher.calculate_distribution(total_processes=5000)

        # 5000 processes / 100 per batch = 50 batches
        assert stats["total_batches"] == 50
        assert stats["batch_size"] == 100
        assert stats["delay_seconds"] == 36.0

        # 50 batches * 36s = 1800s = 0.5 hours
        assert stats["total_time_hours"] == 0.5
        assert stats["fits_in_window"] is True

    def test_distribute_evenly(self, batcher):
        """Test even distribution across time window."""
        cnj_numbers = [f"000000{i:03d}-00.2023.8.00.0000" for i in range(300)]
        tenant_id = uuid4()

        batches = batcher.distribute_evenly(cnj_numbers, tenant_id, window_hours=1)

        # Should create 3 batches
        assert len(batches) == 3

        # Calculate actual delays
        delay1 = (batches[1].scheduled_at - batches[0].scheduled_at).total_seconds()
        delay2 = (batches[2].scheduled_at - batches[1].scheduled_at).total_seconds()

        # Delays should be approximately equal and >= 36s
        assert delay1 >= 36.0
        assert delay2 >= 36.0
        assert abs(delay1 - delay2) < 1.0  # Should be very similar

    def test_can_process_now(self, batcher):
        """Test checking if batch can be processed."""
        # First batch can always be processed
        assert batcher.can_process_now(None) is True

        # After processing, need to wait
        last_batch_time = datetime.utcnow()
        assert batcher.can_process_now(last_batch_time) is False

        # After waiting 36+ seconds, can process again
        last_batch_time = datetime.utcnow() - timedelta(seconds=37)
        assert batcher.can_process_now(last_batch_time) is True

    def test_get_next_batch_time(self, batcher):
        """Test calculating next batch time."""
        last_batch_time = datetime.utcnow()
        next_batch_time = batcher.get_next_batch_time(last_batch_time)

        # Should be 36 seconds later
        expected = last_batch_time + timedelta(seconds=36)
        assert abs((next_batch_time - expected).total_seconds()) < 0.1

    @pytest.mark.asyncio
    async def test_process_batches_sequentially(self, batcher):
        """Test sequential batch processing."""
        cnj_numbers = [f"000000{i:02d}-00.2023.8.00.0000" for i in range(150)]
        tenant_id = uuid4()

        # Create batches with short delays for testing
        batcher.delay_seconds = 0.5
        batches = batcher.create_batches(cnj_numbers, tenant_id)

        # Mock process function
        processed_batches = []

        async def mock_process(batch: Batch):
            processed_batches.append(batch.batch_id)
            return f"Processed batch {batch.batch_id}"

        # Process batches
        start = datetime.utcnow()
        results = await batcher.process_batches_sequentially(batches, mock_process)
        duration = (datetime.utcnow() - start).total_seconds()

        # Verify all batches were processed
        assert len(results) == 2
        assert processed_batches == [0, 1]

        # Should take approximately 0.5 seconds (one delay between 2 batches)
        assert 0.4 <= duration <= 1.0

    def test_empty_cnj_list(self, batcher):
        """Test handling of empty CNJ list."""
        batches = batcher.create_batches([], uuid4())
        assert len(batches) == 0
