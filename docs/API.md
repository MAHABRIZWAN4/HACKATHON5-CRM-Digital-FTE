# API Documentation

Base URL: `http://localhost:8001`

## Authentication

Currently, the API does not require authentication for most endpoints. The dashboard has password protection on the frontend.

## Endpoints

### Health Check

#### GET /health

Check if the API server is running and database is connected.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### Support Form

#### POST /support

Submit a support request via web form.

**Request Body:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "subject": "Need help with billing",
  "message": "I was charged twice for my subscription"
}
```

**Response (201 Created):**
```json
{
  "status": "success",
  "channel": "web_form",
  "ticket_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "message": "Support request submitted successfully"
}
```

**Error Response (400 Bad Request):**
```json
{
  "status": "error",
  "channel": "web_form",
  "message": "Invalid email format"
}
```

---

#### GET /support/test-db

Test database connectivity and get ticket statistics.

**Response:**
```json
{
  "tickets": 42,
  "customers": 28,
  "last_ticket": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "title": "Billing Issue",
    "status": "open",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

---

### Webhooks

#### POST /webhooks/gmail

Handle incoming Gmail webhook events.

**Request Body:**
```json
{
  "message_id": "msg_123456",
  "thread_id": "thread_789",
  "from": "customer@example.com",
  "subject": "Support Request",
  "body": "I need help with my account",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "channel": "gmail",
  "ticket_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "message": "Gmail webhook processed successfully"
}
```

**Error Response (400 Bad Request):**
```json
{
  "status": "error",
  "channel": "gmail",
  "message": "Missing required field: from"
}
```

---

#### POST /webhooks/whatsapp

Handle incoming WhatsApp webhook events from Twilio.

**Headers:**
```
X-Twilio-Signature: <signature_for_validation>
```

**Request Body (Form Data):**
```
MessageSid=SM123456
From=whatsapp:+1234567890
To=whatsapp:+14155238886
Body=I need help with my order
NumMedia=0
```

**Response (200 OK):**
```json
{
  "status": "success",
  "channel": "whatsapp",
  "ticket_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "response_sent": true,
  "message": "WhatsApp message processed successfully"
}
```

**Error Response (400 Bad Request):**
```json
{
  "status": "error",
  "channel": "whatsapp",
  "message": "Invalid webhook signature"
}
```

---

### Dashboard

#### GET /dashboard/escalations

Get all escalated tickets for the dashboard.

**Response (200 OK):**
```json
{
  "success": true,
  "escalations": [
    {
      "ticket_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "customer_email": "customer@example.com",
      "customer_name": "John Doe",
      "title": "Billing Issue - Urgent",
      "reason": "billing_complaint",
      "urgency": "high",
      "status": "escalated",
      "created_at": "2024-01-15T10:30:00Z",
      "escalated_at": "2024-01-15T10:35:00Z"
    }
  ],
  "count": 1
}
```

**Error Response (500 Internal Server Error):**
```json
{
  "success": false,
  "error": "Database connection failed",
  "escalations": []
}
```

---

#### POST /dashboard/escalations/{ticket_id}/resolve

Mark an escalated ticket as resolved.

**Path Parameters:**
- `ticket_id` (string, required): UUID of the ticket to resolve

**Response (200 OK):**
```json
{
  "success": true,
  "ticket_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "message": "Ticket marked as resolved"
}
```

**Error Response (404 Not Found):**
```json
{
  "success": false,
  "error": "Ticket not found or not escalated"
}
```

**Error Response (500 Internal Server Error):**
```json
{
  "success": false,
  "error": "Database error"
}
```

---

## Data Models

### WebFormRequest
```typescript
{
  name: string;        // Customer name (required)
  email: string;       // Valid email address (required)
  subject: string;     // Ticket subject (required)
  message: string;     // Ticket message/description (required)
}
```

### Escalation
```typescript
{
  ticket_id: string;           // UUID
  customer_email: string;      // Customer email
  customer_name: string;       // Customer name
  title: string;               // Ticket title
  reason: string;              // Escalation reason
  urgency: "high" | "medium" | "low";
  status: "escalated" | "resolved";
  created_at: string;          // ISO 8601 timestamp
  escalated_at: string;        // ISO 8601 timestamp
}
```

---

## Error Codes

| Status Code | Description |
|------------|-------------|
| 200 | Success |
| 201 | Created (new resource) |
| 400 | Bad Request (invalid input) |
| 404 | Not Found |
| 500 | Internal Server Error |

---

## Rate Limiting

Currently, there is no rate limiting implemented. For production use, consider adding rate limiting middleware.

---

## CORS Configuration

The API allows requests from all origins (`*`) in development. Update CORS settings in production:

```python
# app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Testing with cURL

### Submit Support Request
```bash
curl -X POST http://localhost:8001/support \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "subject": "Test Issue",
    "message": "This is a test message"
  }'
```

### Get Escalations
```bash
curl http://localhost:8001/dashboard/escalations
```

### Resolve Ticket
```bash
curl -X POST http://localhost:8001/dashboard/escalations/TICKET_ID/resolve
```

### Health Check
```bash
curl http://localhost:8001/health
```

---

## WebSocket Support

Currently not implemented. Future versions may include WebSocket support for real-time dashboard updates.

---

## API Versioning

Current version: v1 (implicit)

Future versions will use URL versioning:
- `/api/v1/...`
- `/api/v2/...`

---

## Additional Resources

- **OpenAPI/Swagger Docs**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
- **GitHub Repository**: [Link to repo]
- **Support**: support@yourcompany.com
