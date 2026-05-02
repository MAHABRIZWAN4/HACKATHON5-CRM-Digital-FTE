# Customer Success Digital FTE

An AI-powered customer success platform that handles support tickets across multiple channels (Web Form, Gmail, WhatsApp) with intelligent routing, escalation, and automated responses.

## 🎯 Business Problem Solved

Traditional customer support teams struggle with:
- **Manual ticket routing** across multiple channels
- **Delayed response times** during high volume
- **Inconsistent support quality** across agents
- **Missed escalations** for critical issues
- **Poor visibility** into support metrics

This platform automates customer success operations using AI to:
- ✅ Automatically route and respond to tickets
- ✅ Detect and escalate critical issues
- ✅ Provide 24/7 intelligent support
- ✅ Maintain consistent response quality
- ✅ Real-time dashboard for human oversight

## 🚀 Key Features

### Multi-Channel Support
- **Web Form**: Direct submission via frontend
- **Gmail**: Email integration with OAuth
- **WhatsApp**: Twilio integration for messaging

### Intelligent Agent
- **AI-Powered Responses**: Uses Groq LLM for natural language understanding
- **Knowledge Base Search**: Semantic search with vector embeddings
- **Auto-Escalation**: Detects billing issues, legal threats, aggressive language
- **Customer History**: Tracks conversation context

### Real-Time Dashboard
- **Escalation Monitoring**: View all escalated tickets
- **One-Click Resolution**: Mark tickets as resolved
- **Live Updates**: Auto-refresh every 30 seconds
- **Mobile Responsive**: Works on all devices

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CUSTOMER CHANNELS                        │
├──────────────┬──────────────────┬─────────────────────────┤
│  Web Form    │      Gmail       │      WhatsApp           │
│ (localhost)  │  (OAuth + Poll)  │   (Twilio Webhook)      │
└──────┬───────┴────────┬─────────┴──────────┬──────────────┘
       │                │                     │
       └────────────────┼─────────────────────┘
                        │
                        ▼
              ┌─────────────────────┐
              │   FastAPI Backend   │
              │   (Port 8001)       │
              └──────────┬──────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
    ┌────────┐    ┌──────────┐   ┌──────────┐
    │ Ticket │    │   AI     │   │ Knowledge│
    │ System │    │  Agent   │   │   Base   │
    └────┬───┘    └────┬─────┘   └────┬─────┘
         │             │              │
         └─────────────┼──────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │   PostgreSQL    │
              │   + pgvector    │
              └─────────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │    Dashboard    │
              │  (localhost:3000)│
              └─────────────────┘
```

## 🛠️ Tech Stack

### Backend
- **FastAPI**: Modern Python web framework
- **PostgreSQL**: Relational database with pgvector
- **asyncpg**: Async database driver
- **Groq API**: LLM for intelligent responses
- **Twilio**: WhatsApp integration
- **Gmail API**: Email integration

### Frontend
- **Next.js 15**: React framework
- **TypeScript**: Type-safe JavaScript
- **Tailwind CSS**: Utility-first styling

### AI/ML
- **Groq LLM**: llama-3.3-70b-versatile
- **Sentence Transformers**: Text embeddings
- **pgvector**: Vector similarity search

## 📋 Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **PostgreSQL 14+** with pgvector extension
- **Gmail Account** (for email integration)
- **Twilio Account** (for WhatsApp)
- **Groq API Key** (for AI agent)

## 🔧 Installation

### 1. Clone Repository
```bash
git clone <repository-url>
cd "Hackathon 5"
```

### 2. Backend Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Create .env file (see .env.example)
cp .env.example .env
```

### 3. Frontend Setup

```bash
cd frontend
npm install
cd ..
```

### 4. Database Setup

```bash
# Create database
psql -U postgres
CREATE DATABASE fte_db;
\c fte_db
CREATE EXTENSION vector;
\q

# Run schema
psql -U postgres -d fte_db -f schema.sql

# Seed knowledge base
python scripts/seed_knowledge_base.py
```

## 🔐 Environment Variables

Create `.env` file in project root:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=fte_db

# Connection Pool Settings
DB_POOL_MIN_SIZE=10
DB_POOL_MAX_SIZE=20
DB_POOL_TIMEOUT=30

# Gmail Configuration
GMAIL_ADDRESS=your-email@gmail.com
GMAIL_POLLING_ENABLED=false

# Groq Configuration (AI Agent)
GROQ_API_KEY=your_groq_api_key
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=llama-3.3-70b-versatile

# Support Team Configuration
SUPPORT_EMAIL=support@yourcompany.com

# Twilio Configuration (WhatsApp)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Dashboard Password
DASHBOARD_PASSWORD=admin123
```

### Gmail OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download `credentials.json` to project root
6. Run authentication:
```bash
python scripts/gmail_auth.py
```
7. This creates `token.json` for API access

### Twilio WhatsApp Setup

1. Sign up at [Twilio](https://www.twilio.com/)
2. Get WhatsApp Sandbox number
3. Add credentials to `.env`
4. Configure webhook URL (use ngrok for local testing)

## 🚀 Running the Project

### Start Backend (Port 8001)
```bash
# From project root
uvicorn app.main:app --reload --port 8001
```

### Start Frontend (Port 3000)
```bash
# In new terminal
cd frontend
npm run dev
```

### Access Points
- **Web Form**: http://localhost:3000
- **Dashboard**: http://localhost:3000/dashboard
- **API Docs**: http://localhost:8001/docs
- **Health Check**: http://localhost:8001/health

## 🧪 Testing

### Run All Tests
```bash
python -m pytest tests/ -v
```

### Run Specific Test Suites
```bash
# Unit tests
python -m pytest tests/test_agent.py -v
python -m pytest tests/test_handlers.py -v

# E2E tests (requires running server)
python -m pytest tests/test_e2e.py -v
```

### Test Coverage
```bash
pytest --cov=app tests/
```

## 📱 Channel Testing

### 1. Web Form Testing
1. Open http://localhost:3000
2. Fill out support form:
   - Name: Test User
   - Email: test@example.com
   - Subject: Test Issue
   - Message: I need help with...
3. Submit form
4. Check dashboard for new ticket

### 2. Gmail Testing
1. Enable polling in `.env`: `GMAIL_POLLING_ENABLED=true`
2. Restart backend
3. Send email to configured Gmail address
4. Agent processes email automatically
5. Check dashboard for ticket

### 3. WhatsApp Testing

#### Setup Ngrok (for local testing)
```bash
# Install ngrok
npm install -g ngrok

# Start ngrok tunnel
ngrok http 8001

# Copy HTTPS URL (e.g., https://abc123.ngrok.io)
```

#### Configure Twilio Webhook
1. Go to Twilio Console
2. Navigate to WhatsApp Sandbox
3. Set webhook URL: `https://abc123.ngrok.io/webhooks/whatsapp`
4. Save configuration

#### Send Test Message
1. Join WhatsApp Sandbox (follow Twilio instructions)
2. Send message to sandbox number
3. Agent responds automatically
4. Check dashboard for ticket

## 📊 Dashboard

### Access Dashboard
- URL: http://localhost:3000/dashboard
- Password: Set in `.env` as `DASHBOARD_PASSWORD`

### Features
- **Real-time Updates**: Auto-refresh every 30 seconds
- **Escalation List**: All escalated tickets with details
- **Quick Actions**: One-click resolution
- **Stats Overview**: Total, high urgency, pending counts
- **Mobile Responsive**: Card layout on mobile devices

### Dashboard Columns
- **Ticket ID**: Unique identifier
- **Customer**: Name and email
- **Reason**: Escalation reason
- **Urgency**: High/Medium/Low
- **Created At**: Timestamp
- **Status**: Escalated/Resolved
- **Action**: Resolve button

## 🔍 Manual Testing Guide

### Test Escalation Flow
1. Submit ticket with billing complaint:
   - Message: "I was charged twice! I need a refund immediately!"
2. Check dashboard - should be escalated
3. Verify urgency level is "high"
4. Click "Mark as Resolved"
5. Ticket should disappear from dashboard

### Test Cross-Channel Customer
1. Submit web form with email: test@example.com
2. Send Gmail from same email
3. Check database - should have same customer_id
4. Verify 2 tickets linked to same customer

### Test AI Responses
1. Submit simple question: "What are your business hours?"
2. Agent should respond from knowledge base
3. No escalation should occur
4. Response should be natural and helpful

## 🐛 Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -U postgres -d fte_db -c "SELECT 1;"
```

### Gmail Polling Not Working
- Verify `credentials.json` exists
- Check `token.json` is valid
- Ensure Gmail API is enabled
- Check `.env` has correct email

### WhatsApp Webhook Failing
- Verify ngrok is running
- Check Twilio webhook URL is correct
- Ensure backend is accessible
- Check Twilio credentials in `.env`

### Agent Not Responding
- Verify Groq API key is valid
- Check API rate limits
- Review backend logs for errors
- Ensure knowledge base is seeded

## 📚 Additional Documentation

- **API Documentation**: See [docs/API.md](docs/API.md)
- **Database Schema**: See [schema.sql](schema.sql)
- **Test Documentation**: See [tests/README.md](tests/README.md)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Run tests
5. Submit pull request

## 📄 License

MIT License - See LICENSE file for details

## 👥 Support

For issues or questions:
- Create GitHub issue
- Email: support@yourcompany.com
- Check documentation: [docs/](docs/)

---

**Built with ❤️ for Customer Success Teams**
