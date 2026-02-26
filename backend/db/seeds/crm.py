"""Seed data for CRM: leads and clients."""

import asyncio
import random
from datetime import datetime, timedelta
from uuid import UUID
from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.lead import Lead, LeadStatus, LeadStage, LeadSource
from app.db.models.client import Client, ClientStatus
from app.db.models.timeline_event import TimelineEvent
from app.db.models.client_note import ClientNote
from .tenant import DEMO_TENANT_ID

fake = Faker("pt_BR")


async def seed_leads(
    session: AsyncSession,
    tenant_id: UUID,
    user_ids: list[UUID],
    count: int = 20
) -> list[Lead]:
    """
    Create demo leads in different stages.
    
    Args:
        session: Database session
        tenant_id: Tenant ID
        user_ids: List of user IDs to assign leads to
        count: Number of leads to create
        
    Returns:
        List of created leads
    """
    stages = [
        (LeadStage.NEW, 6),
        (LeadStage.CONTACTED, 5),
        (LeadStage.QUALIFIED, 4),
        (LeadStage.PROPOSAL, 3),
        (LeadStage.NEGOTIATION, 2),
    ]
    
    sources = [
        LeadSource.CHATWIT,
        LeadSource.WEBSITE,
        LeadSource.REFERRAL,
        LeadSource.SOCIAL_MEDIA,
    ]
    
    leads = []
    lead_idx = 0
    
    for stage, stage_count in stages:
        for _ in range(stage_count):
            lead_idx += 1
            
            # Generate lead data
            full_name = fake.name()
            phone = fake.phone_number()
            email = fake.email()
            source = random.choice(sources)
            
            # Score increases with stage progression
            base_score = {
                LeadStage.NEW: 20,
                LeadStage.CONTACTED: 40,
                LeadStage.QUALIFIED: 60,
                LeadStage.PROPOSAL: 75,
                LeadStage.NEGOTIATION: 85,
            }[stage]
            score = base_score + random.randint(-10, 10)
            
            # AI summary based on stage
            ai_summaries = {
                LeadStage.NEW: f"Lead recebido via {source.value}. Aguardando primeiro contato.",
                LeadStage.CONTACTED: f"Primeiro contato realizado. Interesse em {random.choice(['direito trabalhista', 'direito civil', 'direito de família'])}.",
                LeadStage.QUALIFIED: f"Lead qualificado. Caso: {random.choice(['ação trabalhista', 'divórcio', 'inventário', 'ação de cobrança'])}. Orçamento solicitado.",
                LeadStage.PROPOSAL: "Proposta enviada. Aguardando retorno do cliente.",
                LeadStage.NEGOTIATION: "Em negociação. Cliente solicitou ajustes na proposta.",
            }
            
            ai_actions = {
                LeadStage.NEW: "Realizar primeiro contato em até 24h",
                LeadStage.CONTACTED: "Qualificar necessidade e enviar formulário",
                LeadStage.QUALIFIED: "Preparar proposta comercial",
                LeadStage.PROPOSAL: "Follow-up em 3 dias",
                LeadStage.NEGOTIATION: "Revisar proposta e agendar reunião",
            }
            
            lead = Lead(
                tenant_id=tenant_id,
                assigned_to=random.choice(user_ids),
                full_name=full_name,
                phone=phone,
                email=email,
                source=source,
                chatwit_contact_id=f"chatwit_{lead_idx}" if source == LeadSource.CHATWIT else None,
                stage=stage,
                score=score,
                ai_summary=ai_summaries[stage],
                ai_recommended_action=ai_actions[stage],
                status=LeadStatus.ACTIVE,
                metadata={
                    "case_type": random.choice(["trabalhista", "civil", "família", "criminal"]),
                    "urgency": random.choice(["baixa", "média", "alta"]),
                    "estimated_value": random.randint(5000, 50000),
                }
            )
            
            session.add(lead)
            leads.append(lead)
    
    await session.flush()
    
    # Create timeline events for leads
    for lead in leads:
        # Initial contact event
        event = TimelineEvent(
            tenant_id=tenant_id,
            entity_type="lead",
            entity_id=lead.id,
            event_type="lead_created",
            title="Lead criado",
            description=f"Lead {lead.full_name} criado via {lead.source.value}",
            source="system",
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
        )
        session.add(event)
        
        # Additional events for advanced stages
        if lead.stage in [LeadStage.CONTACTED, LeadStage.QUALIFIED, LeadStage.PROPOSAL, LeadStage.NEGOTIATION]:
            event = TimelineEvent(
                tenant_id=tenant_id,
                entity_type="lead",
                entity_id=lead.id,
                event_type="lead_contacted",
                title="Primeiro contato realizado",
                description="Lead contatado via WhatsApp. Demonstrou interesse.",
                source="user",
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 20))
            )
            session.add(event)
        
        if lead.stage in [LeadStage.QUALIFIED, LeadStage.PROPOSAL, LeadStage.NEGOTIATION]:
            event = TimelineEvent(
                tenant_id=tenant_id,
                entity_type="lead",
                entity_id=lead.id,
                event_type="lead_qualified",
                title="Lead qualificado",
                description="Lead qualificado pela IA. Score: " + str(lead.score),
                source="ai",
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 15))
            )
            session.add(event)
    
    await session.flush()
    
    print(f"✓ Created {len(leads)} leads across different stages")
    return leads


async def seed_clients(
    session: AsyncSession,
    tenant_id: UUID,
    user_ids: list[UUID],
    count: int = 10
) -> list[Client]:
    """
    Create demo clients with notes and interactions.
    
    Args:
        session: Database session
        tenant_id: Tenant ID
        user_ids: List of user IDs to assign clients to
        count: Number of clients to create
        
    Returns:
        List of created clients
    """
    clients = []
    
    for i in range(count):
        full_name = fake.name()
        is_company = random.random() < 0.3  # 30% companies
        
        client = Client(
            tenant_id=tenant_id,
            assigned_to=random.choice(user_ids),
            full_name=full_name if not is_company else fake.company(),
            cpf_cnpj=fake.cpf() if not is_company else fake.cnpj(),
            email=fake.email(),
            phone=fake.phone_number(),
            address={
                "street": fake.street_address(),
                "city": fake.city(),
                "state": fake.state_abbr(),
                "zip_code": fake.postcode(),
            },
            chatwit_contact_id=f"chatwit_client_{i+1}" if random.random() < 0.7 else None,
            status=ClientStatus.ACTIVE,
            health_score=random.randint(70, 100),
            notes=f"Cliente desde {fake.date_between(start_date='-2y', end_date='today').strftime('%d/%m/%Y')}. "
                  f"{random.choice(['Muito satisfeito com os serviços.', 'Cliente exigente mas pontual.', 'Bom relacionamento.', 'Cliente VIP.'])}",
            custom_fields={
                "preferred_contact": random.choice(["whatsapp", "email", "phone"]),
                "language": "pt-BR",
                "timezone": "America/Sao_Paulo",
            }
        )
        
        session.add(client)
        clients.append(client)
    
    await session.flush()
    
    # Create client notes
    for client in clients:
        num_notes = random.randint(1, 4)
        for j in range(num_notes):
            note = ClientNote(
                tenant_id=tenant_id,
                client_id=client.id,
                author_id=random.choice(user_ids),
                content=random.choice([
                    "Cliente solicitou atualização sobre o processo.",
                    "Reunião agendada para próxima semana.",
                    "Cliente enviou novos documentos.",
                    "Pagamento de honorários recebido.",
                    "Cliente muito satisfeito com andamento do caso.",
                    "Necessário agendar audiência.",
                ]),
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 60))
            )
            session.add(note)
        
        # Create timeline events
        events_data = [
            ("client_created", "Cliente cadastrado", "Cliente cadastrado no sistema"),
            ("meeting", "Reunião realizada", "Reunião inicial para discussão do caso"),
            ("document_received", "Documentos recebidos", "Cliente enviou documentação necessária"),
            ("payment_received", "Pagamento recebido", f"Honorários recebidos: R$ {random.randint(2000, 10000)}"),
        ]
        
        for event_type, title, description in random.sample(events_data, k=random.randint(2, 4)):
            event = TimelineEvent(
                tenant_id=tenant_id,
                entity_type="client",
                entity_id=client.id,
                event_type=event_type,
                title=title,
                description=description,
                source="user",
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 90))
            )
            session.add(event)
    
    await session.flush()
    
    print(f"✓ Created {len(clients)} clients with notes and interactions")
    return clients


async def run_crm_seed(
    session: AsyncSession,
    tenant_id: UUID,
    user_ids: list[UUID]
) -> dict:
    """
    Run complete CRM seed.
    
    Args:
        session: Database session
        tenant_id: Tenant ID
        user_ids: List of user IDs
        
    Returns:
        Dictionary with created leads and clients
    """
    print("\n=== Seeding CRM Data (Leads & Clients) ===")
    
    leads = await seed_leads(session, tenant_id, user_ids, count=20)
    clients = await seed_clients(session, tenant_id, user_ids, count=10)
    
    await session.commit()
    
    print(f"\n✓ CRM seed completed: {len(leads)} leads, {len(clients)} clients")
    
    return {
        "leads": leads,
        "clients": clients,
    }


if __name__ == "__main__":
    # For standalone testing
    from app.db.engine import AsyncSessionLocal
    from .tenant import run_tenant_seed
    
    async def main():
        async with AsyncSessionLocal() as session:
            # Need tenant and users first
            tenant_data = await run_tenant_seed(session)
            user_ids = [u.id for u in tenant_data["users"]]
            
            await run_crm_seed(session, DEMO_TENANT_ID, user_ids)
    
    asyncio.run(main())
