"""Seed data for legal cases and movements."""

import asyncio
import hashlib
import random
from datetime import date, datetime, timedelta
from uuid import UUID
from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.legal_case import LegalCase
from app.db.models.case_movement import CaseMovement
from app.db.models.client import Client
from .tenant import DEMO_TENANT_ID

fake = Faker("pt_BR")


def generate_cnj_number(year: int = None) -> str:
    """
    Generate a realistic (fake) CNJ process number.
    Format: NNNNNNN-DD.AAAA.J.TR.OOOO
    
    Args:
        year: Year for the process (defaults to random recent year)
        
    Returns:
        CNJ formatted number
    """
    if year is None:
        year = random.randint(2020, 2024)
    
    sequential = random.randint(1, 9999999)  # NNNNNNN
    verification = random.randint(10, 99)     # DD
    segment = random.choice([1, 2, 3, 4, 5, 6, 8])  # J (judicial segment)
    court = random.randint(1, 27)             # TR (tribunal)
    origin = random.randint(1, 9999)          # OOOO
    
    return f"{sequential:07d}-{verification:02d}.{year}.{segment}.{court:02d}.{origin:04d}"


def generate_movement_description(movement_type: str) -> str:
    """Generate realistic movement description based on type."""
    
    descriptions = {
        "Distribuição": [
            "Processo distribuído por sorteio ao Juízo da Vara Cível",
            "Distribuição automática para a Vara do Trabalho",
            "Processo distribuído para análise inicial",
        ],
        "Citação": [
            "Expedido mandado de citação do réu",
            "Citação realizada por oficial de justiça",
            "Citação por edital publicada",
        ],
        "Contestação": [
            "Apresentada contestação pela parte ré",
            "Juntada aos autos contestação com documentos",
            "Defesa apresentada tempestivamente",
        ],
        "Audiência": [
            "Designada audiência de conciliação para " + (date.today() + timedelta(days=random.randint(30, 90))).strftime("%d/%m/%Y"),
            "Realizada audiência de instrução e julgamento",
            "Audiência redesignada a pedido das partes",
        ],
        "Sentença": [
            "Proferida sentença de procedência do pedido",
            "Sentença de improcedência publicada",
            "Julgado procedente em parte o pedido inicial",
        ],
        "Recurso": [
            "Interposto recurso de apelação pela parte ré",
            "Apresentadas contrarrazões ao recurso",
            "Recurso recebido e remetido ao Tribunal",
        ],
        "Decisão": [
            "Deferida liminar requerida pela parte autora",
            "Indeferido pedido de tutela de urgência",
            "Decisão interlocutória proferida",
        ],
        "Perícia": [
            "Nomeado perito para realização de perícia técnica",
            "Juntado laudo pericial aos autos",
            "Designada data para perícia médica",
        ],
        "Intimação": [
            "Intimadas as partes para manifestação",
            "Publicada intimação no Diário Oficial",
            "Intimação eletrônica realizada",
        ],
        "Juntada": [
            "Juntada aos autos petição da parte autora",
            "Documentos apresentados pela defesa",
            "Anexados novos elementos de prova",
        ],
    }
    
    movement_type_key = movement_type.split(" - ")[0] if " - " in movement_type else movement_type
    
    if movement_type_key in descriptions:
        return random.choice(descriptions[movement_type_key])
    
    return f"Movimentação processual: {movement_type}"


async def seed_legal_cases(
    session: AsyncSession,
    tenant_id: UUID,
    clients: list[Client],
    count: int = 15
) -> list[LegalCase]:
    """
    Create demo legal cases with realistic CNJ numbers.
    
    Args:
        session: Database session
        tenant_id: Tenant ID
        clients: List of clients to associate cases with
        count: Number of cases to create
        
    Returns:
        List of created legal cases
    """
    case_types = [
        "Ação Trabalhista",
        "Ação de Cobrança",
        "Divórcio Consensual",
        "Inventário",
        "Ação de Despejo",
        "Ação de Indenização",
        "Execução Fiscal",
        "Mandado de Segurança",
    ]
    
    courts = [
        "1ª Vara Cível de São Paulo",
        "2ª Vara do Trabalho de Campinas",
        "Vara de Família de Ribeirão Preto",
        "Juizado Especial Cível de Santos",
        "Vara Federal de São Paulo",
        "Tribunal Regional do Trabalho - 2ª Região",
    ]
    
    statuses = [
        "Em andamento",
        "Aguardando julgamento",
        "Suspenso",
        "Arquivado",
        "Sentenciado",
    ]
    
    legal_cases = []
    
    for i in range(count):
        client = random.choice(clients)
        case_type = random.choice(case_types)
        court = random.choice(courts)
        
        # Generate dates
        filing_date = fake.date_between(start_date="-3y", end_date="-1m")
        last_movement_date = fake.date_between(start_date=filing_date, end_date="today")
        
        # 30% chance of having a deadline
        next_deadline = None
        if random.random() < 0.3:
            next_deadline = fake.date_between(start_date="today", end_date="+60d")
        
        legal_case = LegalCase(
            tenant_id=tenant_id,
            client_id=client.id,
            cnj_number=generate_cnj_number(),
            court=court,
            case_type=case_type,
            subject=f"{case_type} - {random.choice(['Rescisão contratual', 'Danos morais', 'Cobrança de valores', 'Partilha de bens', 'Revisão de cláusulas'])}",
            status=random.choice(statuses),
            plaintiff=client.full_name,
            defendant=fake.name() if random.random() < 0.7 else fake.company(),
            filing_date=filing_date,
            last_movement_date=last_movement_date,
            next_deadline=next_deadline,
            monitoring_enabled=True,
            last_sync_at=datetime.utcnow() - timedelta(hours=random.randint(1, 6)),
            sync_frequency_hours=6,
            custom_fields={
                "case_value": random.randint(10000, 500000),
                "priority": random.choice(["baixa", "média", "alta"]),
                "responsible_lawyer": random.choice(["Dr. João Silva", "Dra. Maria Santos"]),
            }
        )
        
        session.add(legal_case)
        legal_cases.append(legal_case)
    
    await session.flush()
    
    print(f"✓ Created {len(legal_cases)} legal cases with CNJ numbers")
    return legal_cases


async def seed_case_movements(
    session: AsyncSession,
    tenant_id: UUID,
    legal_cases: list[LegalCase],
    min_movements: int = 5,
    max_movements: int = 15
) -> list[CaseMovement]:
    """
    Create case movements for legal cases.
    
    Args:
        session: Database session
        tenant_id: Tenant ID
        legal_cases: List of legal cases
        min_movements: Minimum movements per case
        max_movements: Maximum movements per case
        
    Returns:
        List of created movements
    """
    movement_types = [
        "Distribuição",
        "Citação",
        "Contestação",
        "Audiência",
        "Sentença",
        "Recurso",
        "Decisão",
        "Perícia",
        "Intimação",
        "Juntada",
    ]
    
    all_movements = []
    
    for legal_case in legal_cases:
        num_movements = random.randint(min_movements, max_movements)
        
        # Generate movements chronologically
        start_date = legal_case.filing_date
        current_date = start_date
        
        for i in range(num_movements):
            # Increment date by random days
            days_increment = random.randint(5, 45)
            current_date = current_date + timedelta(days=days_increment)
            
            # Don't create movements in the future
            if current_date > date.today():
                current_date = date.today()
            
            movement_type = random.choice(movement_types)
            description = generate_movement_description(movement_type)
            
            # Create content hash for deduplication
            content = f"{legal_case.cnj_number}_{current_date}_{description}_{i}"
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            
            # Determine importance (20% are important)
            is_important = random.random() < 0.2
            requires_action = is_important and random.random() < 0.5
            
            ai_summary = None
            if is_important:
                summaries = [
                    "Movimentação crítica: prazo para manifestação.",
                    "Decisão favorável ao cliente.",
                    "Audiência designada - necessário preparar cliente.",
                    "Sentença proferida - analisar necessidade de recurso.",
                    "Intimação urgente - prazo de 5 dias.",
                ]
                ai_summary = random.choice(summaries)
            
            movement = CaseMovement(
                tenant_id=tenant_id,
                legal_case_id=legal_case.id,
                movement_date=current_date,
                movement_type=movement_type,
                description=description,
                content_hash=content_hash,
                is_important=is_important,
                ai_summary=ai_summary,
                requires_action=requires_action,
                embedding=None,  # Will be generated by embedding service
            )
            
            session.add(movement)
            all_movements.append(movement)
    
    await session.flush()
    
    print(f"✓ Created {len(all_movements)} case movements")
    print(f"  - Important movements: {sum(1 for m in all_movements if m.is_important)}")
    print(f"  - Requiring action: {sum(1 for m in all_movements if m.requires_action)}")
    
    return all_movements


async def generate_embeddings_for_movements(
    session: AsyncSession,
    movements: list[CaseMovement]
) -> None:
    """
    Generate embeddings for movements (placeholder).
    
    In production, this would call the embedding service.
    For seed data, we'll skip actual embedding generation.
    
    Args:
        session: Database session
        movements: List of movements to generate embeddings for
    """
    print(f"\n⚠ Skipping embedding generation for {len(movements)} movements")
    print("  In production, embeddings would be generated via:")
    print("  - EmbeddingService with OpenAI text-embedding-3-small")
    print("  - Taskiq worker for async processing")
    print("  - pgvector for storage and similarity search")


async def run_legal_cases_seed(
    session: AsyncSession,
    tenant_id: UUID,
    clients: list[Client]
) -> dict:
    """
    Run complete legal cases seed.

    Args:
        session: Database session
        tenant_id: Tenant ID
        clients: List of clients

    Returns:
        Dictionary with created cases and movements
    """
    from sqlalchemy import select, func

    print("\n=== Seeding Legal Cases and Movements ===")

    # Check if data already exists
    case_count = (await session.execute(
        select(func.count()).select_from(LegalCase).where(LegalCase.tenant_id == tenant_id)
    )).scalar_one()

    if case_count > 0:
        print(f"✓ Legal cases already exist ({case_count}), skipping")
        result = await session.execute(select(LegalCase).where(LegalCase.tenant_id == tenant_id))
        legal_cases = list(result.scalars().all())

        mov_count = (await session.execute(
            select(func.count()).select_from(CaseMovement).where(CaseMovement.tenant_id == tenant_id)
        )).scalar_one()

        print(f"✓ Case movements already exist ({mov_count}), skipping")

        return {
            "legal_cases": legal_cases,
            "movements": [],
        }

    legal_cases = await seed_legal_cases(session, tenant_id, clients, count=15)
    movements = await seed_case_movements(session, tenant_id, legal_cases)

    # Note: Skipping actual embedding generation for seed data
    await generate_embeddings_for_movements(session, movements)

    await session.commit()

    print(f"\n✓ Legal cases seed completed: {len(legal_cases)} cases, {len(movements)} movements")

    return {
        "legal_cases": legal_cases,
        "movements": movements,
    }


if __name__ == "__main__":
    # For standalone testing
    from app.db.engine import AsyncSessionLocal
    from .tenant import run_tenant_seed
    from .crm import run_crm_seed
    
    async def main():
        async with AsyncSessionLocal() as session:
            # Need tenant, users, and clients first
            tenant_data = await run_tenant_seed(session)
            user_ids = [u.id for u in tenant_data["users"]]
            
            crm_data = await run_crm_seed(session, DEMO_TENANT_ID, user_ids)
            
            await run_legal_cases_seed(session, DEMO_TENANT_ID, crm_data["clients"])
    
    asyncio.run(main())
