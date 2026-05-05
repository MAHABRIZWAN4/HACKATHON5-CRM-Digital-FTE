# Hugging Face Spaces Deployment Guide

## Quick Deploy to Hugging Face Spaces

This guide will help you deploy the Customer Success Digital FTE to Hugging Face Spaces in demo mode (without database).

### Prerequisites

- Hugging Face account ([Sign up here](https://huggingface.co/join))
- Git installed on your machine
- Groq API key ([Get one here](https://console.groq.com/))

### Step 1: Create a New Space

1. Go to [Hugging Face Spaces](https://huggingface.co/spaces)
2. Click **"Create new Space"**
3. Fill in the details:
   - **Space name**: `customer-success-fte` (or your choice)
   - **License**: MIT
   - **Select SDK**: Docker
   - **Space hardware**: CPU basic (free tier works fine)
4. Click **"Create Space"**

### Step 2: Configure Space Settings

1. Go to your Space's **Settings** tab
2. Scroll to **"Repository secrets"**
3. Add the following secrets:
   - `GROQ_API_KEY`: Your Groq API key
   - `DASHBOARD_PASSWORD`: Your dashboard password (optional, default: demo123)

### Step 3: Push Code to Space

```bash
# Clone your Space repository
git clone https://huggingface.co/spaces/YOUR_USERNAME/customer-success-fte
cd customer-success-fte

# Copy your project files
cp -r /path/to/your/project/* .

# Make sure these files are present:
# - Dockerfile
# - requirements.txt
# - app/ directory
# - README.md

# Commit and push
git add .
git commit -m "Initial deployment"
git push
```

### Step 4: Wait for Build

1. Go to your Space page
2. Wait for the Docker build to complete (5-10 minutes)
3. Once built, your app will be live!

### Step 5: Access Your Deployed App

Your app will be available at:
- **Space URL**: `https://huggingface.co/spaces/YOUR_USERNAME/customer-success-fte`
- **API Docs**: `https://YOUR_USERNAME-customer-success-fte.hf.space/docs`
- **Health Check**: `https://YOUR_USERNAME-customer-success-fte.hf.space/health`
- **Dashboard API**: `https://YOUR_USERNAME-customer-success-fte.hf.space/dashboard/escalations`

## Demo Mode Features

When deployed to Hugging Face Spaces, the app runs in **demo mode**:

### ✅ What Works
- Health check endpoint
- API documentation (Swagger UI)
- All API endpoints respond successfully
- Dashboard returns sample escalation data
- Support form accepts submissions (returns demo response)

### ⚠️ Limitations
- No persistent database (data not saved)
- Gmail polling disabled
- WhatsApp webhooks return demo responses
- No real ticket storage

### 🎯 Perfect For
- Showcasing the API structure
- Demonstrating the UI/UX
- Testing API integrations
- Portfolio demonstrations
- Hackathon presentations

## Environment Variables

The following environment variables are automatically set in the Dockerfile:

```env
DISABLE_DB=true                    # Disables database requirement
PYTHONUNBUFFERED=1                 # Python logging
PYTHONDONTWRITEBYTECODE=1          # No .pyc files
```

Additional variables you can set in Space secrets:

```env
GROQ_API_KEY=your_key              # Required for AI features
DASHBOARD_PASSWORD=your_password   # Dashboard access (optional)
APP_NAME=Customer Success FTE      # App name (optional)
DEBUG=false                        # Debug mode (optional)
```

## Troubleshooting

### Build Fails

**Issue**: Docker build fails during pip install

**Solution**: Check that `requirements.txt` is present and properly formatted

### App Won't Start

**Issue**: App starts but health check fails

**Solution**: 
1. Check logs in Space's "Logs" tab
2. Verify `DISABLE_DB=true` is set in Dockerfile
3. Ensure port 7860 is exposed

### API Returns Errors

**Issue**: Endpoints return 500 errors

**Solution**:
1. Check if `GROQ_API_KEY` is set in secrets
2. Review application logs
3. Verify all required files are pushed

### Health Check Shows Unhealthy

**Issue**: `/health` endpoint returns unhealthy status

**Solution**:
1. This should not happen in demo mode
2. Check if `DISABLE_DB` environment variable is properly set
3. Review startup logs for errors

## Updating Your Deployment

To update your deployed app:

```bash
# Make changes to your code
git add .
git commit -m "Update: description of changes"
git push

# Space will automatically rebuild
```

## Local Testing of Demo Mode

Test demo mode locally before deploying:

```bash
# Set environment variable
export DISABLE_DB=true

# Run the app
uvicorn app.main:app --host 0.0.0.0 --port 7860

# Test health check
curl http://localhost:7860/health

# Should return:
# {"status":"healthy","mode":"demo","database":"disabled"}
```

## Production Deployment (With Database)

For production deployment with full features:

1. Use a cloud provider (AWS, GCP, Azure, DigitalOcean)
2. Set up PostgreSQL database with pgvector extension
3. Configure environment variables with real database credentials
4. Set `DISABLE_DB=false` or remove it
5. Enable Gmail polling and WhatsApp webhooks
6. Use proper secrets management

See main README.md for full production setup instructions.

## Support

For issues or questions:
- Check Space logs for errors
- Review this deployment guide
- Open an issue on GitHub
- Contact: support@yourcompany.com

---

**Happy Deploying! 🚀**
