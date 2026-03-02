# Seed Data Usage Guide

## Quick Start

```bash
# Install dependencies (if not already installed)
cd backend
poetry install

# Seed all demo data
python -m cli.seed --all
```

## What Gets Created

### 1. Tenant & Users (--tenant)
- **Tenant**: Demo Law Firm (ID: `00000000-0000-0000-0000-000000000001`)
- **Users**:
  - Admin: `admin@demolawfirm.com` / `admin123`
  - Advogado: `advogado@demolawfirm.com` / `advogado123`
  - Assistente: `assistente@demolawfirm.com` / `assistente123`

### 2. CRM Data (--crm)
- **20 Leads** distributed across funnel stages:
  - 6 New leads
  - 5 Contacted leads
  - 4 Qualified leads
  - 3 Proposal stage leads
  - 2 Negotiation stage leads
- **10 Clients** with:
  - Personal information (CPF/CNPJ, email, phone)
  - Address data
  - 1-4 notes per client
  - 2-4 timeline events per client
  - Health scores (70-100)

### 3. Legal Cases (--cases)
- **15 Judicial Processes** with:
  - Realistic CNJ numbers (format: NNNNNNN-DD.AAAA.J.TR.OOOO)
  - Various case types (Labor, Civil, Family, etc.)
  - Court information
  - Filing dates (1-36 months ago)
  - 30% have upcoming deadlines
- **100+ Case Movements**:
  - 5-15 movements per case
  - Chronologically ordered
  - 20% marked as important
  - AI summaries for important movements
  - Content hashing for deduplication

### 4. AI Configuration (--ai)
- **6 AI Providers** configured:
  - OpenAI GPT-4o-mini (priority 100)
  - OpenAI GPT-4o (priority 90)
  - Anthropic Claude 3.5 Sonnet (priority 80)
  - Anthropic Claude 3.5 Haiku (priority 70)
  - Groq Llama 3.3 70B (priority 60)
  - Groq Llama 3.1 8B (priority 50)

## Command Options

### Seed Everything
```bash
python -m cli.seed --all
```

### Seed Specific Components
```bash
# Only tenant and users
python -m cli.seed --tenant

# CRM data (requires tenant)
python -m cli.seed --crm

# Legal cases (requires tenant and CRM)
python -m cli.seed --cases

# AI configuration (requires tenant)
python -m cli.seed --ai

# Combine multiple
python -m cli.seed --tenant --crm --ai
```

### Reset Database
⚠️ **WARNING**: This will delete ALL data!

```bash
python -m cli.seed --all --reset
```

## Environment Setup

### Required Environment Variables

For functional AI features, set real API keys:

```bash
# .env file
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk-...
ENCRYPTION_KEY=...  # For API key encryption
```

### Database Configuration

Ensure your database is running and configured in `.env`:

```bash
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/jusmonitoria
```

## Testing the Seed Data

### 1. Start the Backend
```bash
python main.py
```

### 2. Access API Documentation
Open http://localhost:8000/docs

### 3. Login with Demo Credentials
Use any of the demo user credentials to authenticate.

### 4. Explore the Data
- View leads in different stages
- Check client profiles with notes
- Browse legal cases with movements
- Test AI provider configurations

## Seed Data Characteristics

### Realistic Brazilian Data
- Names generated with Faker (pt_BR)
- Valid CPF/CNPJ formats
- Brazilian phone numbers
- Brazilian addresses (cities, states)

### AI-Generated Content
- Lead summaries based on stage
- Recommended actions for each lead
- Case movement importance classification
- AI summaries for critical movements

### Chronological Consistency
- Leads created 1-30 days ago
- Clients created 1-90 days ago
- Cases filed 1-36 months ago
- Movements in chronological order

### Multi-Tenant Isolation
- All data associated with demo tenant
- Tenant ID enforced at database level
- Ready for multi-tenant testing

## Troubleshooting

### Import Errors
```bash
# Ensure you're in the backend directory
cd backend
python -m cli.seed --all
```

### Database Connection Errors
```bash
# Check database is running
docker ps | grep postgres

# Test connection
psql -h localhost -U user -d jusmonitoria
```

### Missing Dependencies
```bash
# Install all dependencies
poetry install

# Or with pip
pip install -r requirements.txt
```

### Permission Errors
Ensure database user has necessary permissions:
```sql
GRANT ALL PRIVILEGES ON DATABASE jusmonitoria TO user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO user;
```

## Development Notes

### Embeddings
The seed system creates movement records but **does not generate actual embeddings**. 

To generate embeddings:
1. Ensure OpenAI API key is set
2. Run the embedding worker
3. Or trigger embedding generation via API

### API Keys
Demo seeds use placeholder API keys. For functional AI features:
1. Get real API keys from providers
2. Set them in `.env` file
3. Re-run seed with `--ai` flag

### Customization
To modify seed data:
1. Edit files in `backend/db/seeds/`
2. Adjust counts, data ranges, or content
3. Re-run seed command

## Next Steps

After seeding:

1. **Start Backend**: `python main.py`
2. **Access API Docs**: http://localhost:8000/docs
3. **Login**: Use demo credentials
4. **Test Features**:
   - CRM funnel with leads
   - Client profiles (prontuário 360°)
   - Legal case monitoring
   - AI-powered features

## Support

For issues or questions:
- Check `backend/db/seeds/README.md` for detailed documentation
- Review seed file source code in `backend/db/seeds/`
- Check application logs for errors
