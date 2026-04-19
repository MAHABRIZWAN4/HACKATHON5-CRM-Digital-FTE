# Testing Guide - Backend Fix

## Pre-requisites

### 1. Environment Variables Check
```bash
# Check .env file
cat .env
```

Required variables:
```env
GROQ_API_KEY=your_key_here
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=llama-3.3-70b-versatile

# Gmail (optional)
GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password
```

### 2. Database Check
```bash
# Verify database is running
python -c "from app.db.connection import get_db_pool; import asyncio; asyncio.run(get_db_pool().fetchval('SELECT 1'))"
```

## Testing Steps

### Step 1: Start Backend Server

```bash
cd "F:\Hackathon 5"
python -m uvicorn app.main:app --reload --log-level debug
```

Expected output:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Step 2: Test Web Form Submission

#### Option A: Using Frontend
1. Open frontend application
2. Fill the support form:
   - Name: Test User
   - Email: test@example.com
   - Subject: Login Issue
   - Message: I cannot login to my account
3. Submit form
4. Check response

#### Option B: Using cURL
```bash
curl -X POST http://localhost:8000/api/support/web-form \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "subject": "Login Issue",
    "message": "I cannot login to my account. Please help.",
    "category": "technical"
  }'
```

Expected response:
```json
{
  "status": "success",
  "channel": "web_form",
  "ticket_id": "123",
  "message": "Support request submitted and processed successfully",
  "agent_response": "Hello! I found the solution...",
  "tools_used": 3
}
```

### Step 3: Verify Logs

Check backend logs for:

```
✅ Processing web form submission from: test@example.com
✅ Handling inquiry from test@example.com via web_form
✅ Agent iteration 1
✅ Executing tool: create_ticket with args: {...}
✅ Created ticket: 123
✅ Executing tool: search_knowledge_base with args: {...}
✅ Executing tool: send_response with args: {...}
✅ Email sent to test@example.com
✅ Response sent successfully for ticket 123
✅ Agent completed workflow with send_response
```

### Step 4: Verify Database

```sql
-- Check ticket created
SELECT * FROM tickets ORDER BY created_at DESC LIMIT 1;

-- Check customer created
SELECT * FROM customers WHERE email = 'test@example.com';

-- Check messages
SELECT * FROM messages ORDER BY created_at DESC LIMIT 5;
```

### Step 5: Verify Email Sent

Check email inbox for:
- **Subject:** ✅ Solution: Login Issue
- **From:** Your configured Gmail
- **To:** test@example.com
- **Body:** Should contain ticket ID and solution

## Common Issues & Solutions

### Issue 1: OutputParserException
**Symptom:** Error in logs about parsing LLM output

**Solution:** Already fixed! Agent now uses proper tool calling loop.

### Issue 2: No Email Sent
**Symptom:** Logs show "Gmail not configured"

**Solution:**
1. Add Gmail credentials to .env
2. Enable 2FA on Gmail
3. Generate App Password
4. Use App Password in GMAIL_APP_PASSWORD

### Issue 3: Database Connection Error
**Symptom:** "Connection refused" or "Database not found"

**Solution:**
```bash
# Check PostgreSQL is running
pg_isready

# Restart database
# Windows: Services -> PostgreSQL -> Restart
# Linux: sudo systemctl restart postgresql
```

### Issue 4: Agent Not Using Tools
**Symptom:** Agent gives direct response without tools

**Solution:** Already fixed! Check logs for "Agent iteration" messages.

### Issue 5: Duplicate Tickets
**Symptom:** Multiple tickets for same request

**Solution:** Already fixed! Agent creates ticket, web form handler uses that ticket_id.

## Performance Metrics

Monitor these in logs:

- **Agent Iterations:** Should be 2-4 (create_ticket → search_kb → send_response)
- **Tools Used:** Should be 3+ for successful processing
- **Response Time:** Should be < 10 seconds
- **Email Delivery:** Should be < 2 seconds after send_response

## Debug Mode

For detailed debugging:

```bash
# Set log level to DEBUG
export LOG_LEVEL=DEBUG

# Run with verbose logging
python -m uvicorn app.main:app --reload --log-level debug
```

## Test Cases

### Test Case 1: Simple Query
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "subject": "How to reset password?",
  "message": "I forgot my password and need to reset it.",
  "category": "general"
}
```
**Expected:** Agent finds KB article, sends solution email

### Test Case 2: Technical Issue
```json
{
  "name": "Jane Smith",
  "email": "jane@example.com",
  "subject": "App crashes on startup",
  "message": "The application crashes immediately when I try to open it.",
  "category": "technical"
}
```
**Expected:** Agent searches KB, provides troubleshooting steps

### Test Case 3: Escalation Trigger
```json
{
  "name": "Angry Customer",
  "email": "angry@example.com",
  "subject": "This is unacceptable!",
  "message": "I will contact my lawyer if this is not fixed immediately!",
  "category": "general"
}
```
**Expected:** Agent escalates to human, sends escalation email

## Success Criteria

✅ No OutputParserException errors
✅ Ticket created in database
✅ Customer receives email with solution
✅ Agent uses tools (create_ticket, search_knowledge_base, send_response)
✅ Response time < 10 seconds
✅ Proper error handling and fallbacks

## Next Steps After Testing

1. Monitor production logs
2. Collect customer feedback
3. Tune agent prompts based on results
4. Add more KB articles
5. Implement analytics dashboard

---

**Ready to test!** Start backend server and try submitting a form.
