"""Base agent class for all AI agents."""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.provider_manager import ProviderManager

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for all AI agents.
    
    Provides common functionality for:
    - LLM calls with provider management
    - System prompt definition
    - Context formatting
    - Error handling and logging
    """
    
    def __init__(
        self,
        session: AsyncSession,
        tenant_id: UUID,
    ):
        """
        Initialize base agent.
        
        Args:
            session: Database session
            tenant_id: Tenant ID for isolation
        """
        self.session = session
        self.tenant_id = tenant_id
        self.provider_manager = ProviderManager(session, tenant_id)
    
    @abstractmethod
    def get_agent_name(self) -> str:
        """Return agent name for logging."""
        pass
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return agent-specific system prompt."""
        pass
    
    async def execute(
        self,
        user_message: str,
        context: Optional[dict[str, Any]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Execute agent with dynamic provider routing.
        
        Args:
            user_message: User's message/query
            context: Optional context dictionary
            temperature: Override temperature
            max_tokens: Override max tokens
        
        Returns:
            Agent's response as string
        """
        logger.info(
            f"{self.get_agent_name()} agent executing",
            extra={
                "tenant_id": str(self.tenant_id),
                "message_length": len(user_message),
            },
        )
        
        # Build messages
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
        ]
        
        # Add context if provided
        if context:
            context_str = self._format_context(context)
            messages.append({"role": "system", "content": context_str})
        
        messages.append({"role": "user", "content": user_message})
        
        try:
            # Call LLM with provider fallback
            response = await self.provider_manager.call_llm(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            logger.info(
                f"{self.get_agent_name()} agent completed",
                extra={
                    "tenant_id": str(self.tenant_id),
                    "response_length": len(response),
                },
            )
            
            return response
        
        except Exception as e:
            logger.error(
                f"{self.get_agent_name()} agent failed",
                extra={
                    "tenant_id": str(self.tenant_id),
                    "error": str(e),
                },
            )
            raise
    
    def _format_context(self, context: dict[str, Any]) -> str:
        """
        Format context dictionary for LLM.
        
        Args:
            context: Context dictionary
        
        Returns:
            Formatted context string
        """
        parts = []
        
        if "client" in context:
            parts.append(f"Cliente: {context['client']}")
        
        if "contact" in context:
            parts.append(f"Contato: {context['contact']}")
        
        if "processes" in context:
            parts.append(f"Processos: {context['processes']}")
        
        if "recent_events" in context:
            parts.append(f"Eventos recentes: {context['recent_events']}")
        
        if "movements" in context:
            parts.append(f"Movimentações: {context['movements']}")
        
        # Add any other context fields
        for key, value in context.items():
            if key not in ["client", "contact", "processes", "recent_events", "movements"]:
                parts.append(f"{key}: {value}")
        
        return "\n\n".join(parts)
    
    def parse_json_response(self, response: str) -> dict[str, Any]:
        """
        Parse JSON response from LLM.
        
        Handles cases where LLM wraps JSON in markdown code blocks.
        
        Args:
            response: LLM response string
        
        Returns:
            Parsed JSON as dictionary
        
        Raises:
            ValueError: If response is not valid JSON
        """
        # Remove markdown code blocks if present
        response = response.strip()
        
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]
        
        if response.endswith("```"):
            response = response[:-3]
        
        response = response.strip()
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse JSON response",
                extra={
                    "agent": self.get_agent_name(),
                    "response": response[:200],
                    "error": str(e),
                },
            )
            raise ValueError(f"Invalid JSON response: {e}")
