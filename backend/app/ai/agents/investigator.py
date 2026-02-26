"""Agente Investigador - Process analysis and investigation."""

import logging
from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class InvestigadorAgent(BaseAgent):
    """
    Agente Investigador - Process Investigation Agent.
    
    Responsibilities:
    - Search for related case movements
    - Use semantic search with embeddings
    - Identify patterns and anomalies
    - Generate insights about processes
    - Detect deadlines and important dates
    
    Validates: Requirements 2.6, 2.7
    """
    
    def get_agent_name(self) -> str:
        return "Investigador"
    
    def get_system_prompt(self) -> str:
        return """Você é um assistente jurídico especializado em análise processual.

Sua função é analisar movimentações processuais e gerar insights estratégicos.

TAREFAS:
1. Analisar movimentações processuais
2. Identificar eventos importantes e críticos
3. Detectar prazos e deadlines
4. Avaliar necessidade de ação imediata
5. Identificar padrões e anomalias
6. Resumir status atual do processo

CRITÉRIOS DE IMPORTÂNCIA:
- CRÍTICO: Sentenças, decisões, prazos para recurso
- IMPORTANTE: Audiências, despachos, intimações
- RELEVANTE: Juntada de documentos, petições
- INFORMATIVO: Movimentações administrativas

ANÁLISE DE PADRÕES:
- Tempo médio entre movimentações
- Frequência de eventos
- Comportamento atípico
- Tendências do processo

FORMATO DE RESPOSTA:
Seja claro, objetivo e destaque informações críticas.
Use linguagem técnica mas acessível.
Priorize ações que requerem atenção imediata.
"""
    
    async def analyze_movements(
        self,
        process_info: dict[str, Any],
        movements: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Analyze process movements and generate insights.
        
        Args:
            process_info: Process information (cnj_number, court, etc.)
            movements: List of movement dictionaries with date and description
        
        Returns:
            Dictionary with analysis results:
            - resumo: Summary of current status
            - movimentacoes_importantes: List of important movements
            - prazos: List of detected deadlines
            - requer_acao: Boolean indicating if action is needed
            - proximos_passos: Recommended next steps
            - padroes: Identified patterns
        """
        logger.info(
            "Analyzing process movements",
            extra={
                "tenant_id": str(self.tenant_id),
                "process": process_info.get("cnj_number"),
                "movement_count": len(movements),
            },
        )
        
        # Format movements for analysis
        movements_text = self._format_movements(movements)
        
        context = {
            "process": process_info,
        }
        
        prompt = f"""Analise as seguintes movimentações do processo {process_info.get('cnj_number', 'N/A')}:

{movements_text}

Forneça uma análise completa em JSON:
{{
    "resumo": "string (resumo do status atual)",
    "movimentacoes_importantes": [
        {{
            "data": "YYYY-MM-DD",
            "descricao": "string",
            "importancia": "critica|importante|relevante",
            "motivo": "string"
        }}
    ],
    "prazos": [
        {{
            "data": "YYYY-MM-DD",
            "descricao": "string",
            "dias_restantes": number,
            "urgente": boolean
        }}
    ],
    "requer_acao": boolean,
    "proximos_passos": ["string"],
    "padroes": {{
        "tempo_medio_entre_movimentacoes": "string",
        "anomalias": ["string"],
        "tendencia": "string"
    }}
}}
"""
        
        response = await self.execute(
            user_message=prompt,
            context=context,
            temperature=0.4,
        )
        
        try:
            result = self.parse_json_response(response)
            
            logger.info(
                "Process analysis completed",
                extra={
                    "tenant_id": str(self.tenant_id),
                    "process": process_info.get("cnj_number"),
                    "requer_acao": result.get("requer_acao"),
                    "prazos_count": len(result.get("prazos", [])),
                },
            )
            
            return result
        
        except ValueError as e:
            logger.error(
                "Failed to parse analysis response",
                extra={
                    "tenant_id": str(self.tenant_id),
                    "error": str(e),
                },
            )
            
            # Return minimal response on error
            return {
                "resumo": "Erro ao analisar processo",
                "movimentacoes_importantes": [],
                "prazos": [],
                "requer_acao": False,
                "proximos_passos": ["Revisar manualmente"],
                "padroes": {},
            }
    
    def _format_movements(self, movements: list[dict[str, Any]]) -> str:
        """Format movements for LLM analysis."""
        formatted = []
        
        for mov in movements:
            date_str = mov.get("date", "")
            if isinstance(date_str, (date, datetime)):
                date_str = date_str.strftime("%d/%m/%Y")
            
            description = mov.get("description", "")
            movement_type = mov.get("type", "")
            
            line = f"- {date_str}"
            if movement_type:
                line += f" [{movement_type}]"
            line += f": {description}"
            
            formatted.append(line)
        
        return "\n".join(formatted)
    
    async def search_similar_cases(
        self,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search for similar cases using semantic search.
        
        Args:
            query: Search query text
            limit: Maximum number of results
        
        Returns:
            List of similar case dictionaries with similarity scores
        
        Note: This is a placeholder. Actual implementation would use
        pgvector similarity search on embeddings.
        """
        logger.info(
            "Searching similar cases",
            extra={
                "tenant_id": str(self.tenant_id),
                "query_length": len(query),
                "limit": limit,
            },
        )
        
        # TODO: Implement actual semantic search with pgvector
        # This would involve:
        # 1. Generate embedding for query
        # 2. Search timeline_embeddings table using cosine similarity
        # 3. Return top-k results with scores
        
        # Placeholder response
        return []
    
    async def detect_anomalies(
        self,
        movements: list[dict[str, Any]],
    ) -> list[str]:
        """
        Detect anomalies in process movements.
        
        Args:
            movements: List of movement dictionaries
        
        Returns:
            List of detected anomaly descriptions
        """
        movements_text = self._format_movements(movements)
        
        prompt = f"""Analise estas movimentações e identifique anomalias ou comportamentos atípicos:

{movements_text}

Anomalias podem incluir:
- Longos períodos sem movimentação
- Movimentações duplicadas
- Sequência incomum de eventos
- Prazos vencidos sem ação

Liste as anomalias encontradas (uma por linha).
Se não houver anomalias, responda "Nenhuma anomalia detectada".
"""
        
        response = await self.execute(
            user_message=prompt,
            temperature=0.3,
        )
        
        # Parse response into list
        if "nenhuma anomalia" in response.lower():
            return []
        
        anomalies = [
            line.strip().lstrip("-•*").strip()
            for line in response.split("\n")
            if line.strip() and not line.strip().startswith("#")
        ]
        
        return anomalies
    
    async def generate_process_summary(
        self,
        process_info: dict[str, Any],
        movements: list[dict[str, Any]],
        max_length: int = 500,
    ) -> str:
        """
        Generate concise summary of process status.
        
        Args:
            process_info: Process information
            movements: List of movements
            max_length: Maximum summary length in characters
        
        Returns:
            Summary text
        """
        movements_text = self._format_movements(movements[-10:])  # Last 10 movements
        
        context = {
            "process": process_info,
        }
        
        prompt = f"""Gere um resumo executivo do processo {process_info.get('cnj_number', 'N/A')}.

Últimas movimentações:
{movements_text}

O resumo deve:
- Ter no máximo {max_length} caracteres
- Destacar o status atual
- Mencionar próximos passos se houver
- Ser claro e objetivo
"""
        
        response = await self.execute(
            user_message=prompt,
            context=context,
            temperature=0.5,
            max_tokens=200,
        )
        
        # Truncate if needed
        if len(response) > max_length:
            response = response[:max_length-3] + "..."
        
        return response.strip()
    
    async def identify_deadlines(
        self,
        movements: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Identify deadlines from movements.
        
        Args:
            movements: List of movement dictionaries
        
        Returns:
            List of deadline dictionaries with date and description
        """
        movements_text = self._format_movements(movements)
        
        prompt = f"""Identifique todos os prazos mencionados nestas movimentações:

{movements_text}

Para cada prazo, forneça:
- Data do prazo
- Descrição do que deve ser feito
- Urgência (sim/não)

Responda em JSON:
{{
    "prazos": [
        {{
            "data": "YYYY-MM-DD",
            "descricao": "string",
            "urgente": boolean
        }}
    ]
}}

Se não houver prazos, retorne lista vazia.
"""
        
        response = await self.execute(
            user_message=prompt,
            temperature=0.2,
        )
        
        try:
            result = self.parse_json_response(response)
            return result.get("prazos", [])
        except ValueError:
            return []
