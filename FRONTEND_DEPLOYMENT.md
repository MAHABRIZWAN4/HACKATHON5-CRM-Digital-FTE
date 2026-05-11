# Frontend Deployment Guide - Hugging Face Spaces

## Files Created

✅ `frontend/Dockerfile` - Docker configuration for Hugging Face Spaces
✅ `frontend/.dockerignore` - Files to exclude from Docker build
✅ `frontend/README.md` - Space documentation with metadata
✅ `frontend/.env.example` - Environment variables template
✅ `frontend/next.config.js` - Updated with standalone output mode
✅ `.github/workflows/deploy-frontend.yml` - CI/CD pipeline for auto-deployment

## Deployment Steps

### Step 1: Create New Hugging Face Space

1. Go to https://huggingface.co/spaces
2. Click "Create new Space"
3. Fill in details:
   - **Space name**: `support-system-frontend` (ya koi bhi naam)
   - **License**: Apache 2.0
   - **Select SDK**: Docker
   - **Space hardware**: CPU basic (free tier)
4. Click "Create Space"

### Step 2: Configure GitHub Secrets

Apne GitHub repository mein jao aur Settings > Secrets and variables > Actions mein ye secret add karein:

```
HF_FRONTEND_SPACE_NAME=support-system-frontend
```

**Note**: `HF_TOKEN` aur `HF_USERNAME` already backend deployment ke liye set hain, wo same use honge.

### Step 3: Configure Environment Variables in Hugging Face Space

1. Apni frontend Space mein jao
2. Settings tab pe click karein
3. "Variables and secrets" section mein:
   - Add variable: `NEXT_PUBLIC_API_URL`
   - Value: Apni backend Space ka URL (e.g., `https://your-username-backend-space.hf.space`)

### Step 4: Deploy

#### Option A: Automatic Deployment (Recommended)

```bash
# Frontend folder mein koi bhi change karo aur commit/push karo
git add .
git commit -m "Deploy frontend to Hugging Face Spaces"
git push origin main
```

GitHub Actions automatically frontend ko deploy kar dega.

#### Option B: Manual Deployment

```bash
cd frontend

# Initialize git in frontend directory
git init
git add .
git commit -m "Initial frontend deployment"

# Add Hugging Face remote
git remote add hf https://YOUR_USERNAME:YOUR_HF_TOKEN@huggingface.co/spaces/YOUR_USERNAME/support-system-frontend

# Push to Hugging Face
git push hf main --force
```

### Step 5: Verify Deployment

1. Hugging Face Space pe jao
2. "Building" status dekho
3. Build complete hone ke baad "App" tab pe click karein
4. Frontend application running honi chahiye on port 7860

## Important Notes

### Backend URL Configuration

Frontend ko backend se connect karne ke liye:

1. Backend Space ka URL copy karein (e.g., `https://username-backend-space.hf.space`)
2. Frontend Space settings mein `NEXT_PUBLIC_API_URL` environment variable set karein
3. Space ko restart karein (Settings > Factory reboot)

### API Calls in Frontend Code

Agar aapke frontend code mein API calls hardcoded hain, to unhe update karein:

```javascript
// Before
const API_URL = 'http://localhost:8000';

// After
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
```

### CORS Configuration

Backend mein CORS properly configure hona chahiye frontend ke URL ke liye. Backend code mein check karein:

```python
# app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://your-username-frontend-space.hf.space"  # Add this
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Troubleshooting

### Build Fails

- Check Dockerfile syntax
- Verify all dependencies in package.json
- Check build logs in Hugging Face Space

### App Not Loading

- Verify port 7860 is exposed
- Check environment variables are set correctly
- Look at runtime logs in Space

### API Connection Issues

- Verify `NEXT_PUBLIC_API_URL` is set correctly
- Check backend CORS configuration
- Ensure backend Space is running

## Local Testing

Docker build locally test karne ke liye:

```bash
cd frontend

# Build Docker image
docker build -t frontend-test .

# Run container
docker run -p 7860:7860 -e NEXT_PUBLIC_API_URL=http://localhost:8000 frontend-test
```

Browser mein `http://localhost:7860` pe jao.

## Next Steps

1. ✅ Backend deployed (already done)
2. ✅ Frontend Dockerfile created
3. ⏳ Create Hugging Face Space for frontend
4. ⏳ Configure GitHub secrets
5. ⏳ Push code to trigger deployment
6. ⏳ Configure environment variables
7. ⏳ Test frontend-backend connection

---

**Ready to deploy!** 🚀
