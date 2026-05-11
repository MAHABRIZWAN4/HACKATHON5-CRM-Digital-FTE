---
title: Support System Frontend
emoji: 🎫
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
app_port: 7860
---

# Support System Frontend

This is the frontend application for the AI-powered support ticket system built with Next.js.

## Features

- Modern React-based UI with Next.js 15
- Tailwind CSS for styling
- Framer Motion animations
- Responsive design

## Environment Variables

Set the following environment variable in your Hugging Face Space settings:

- `NEXT_PUBLIC_API_URL`: Backend API URL (e.g., your deployed backend Space URL)

## Deployment

This application is configured to run on Hugging Face Spaces using Docker.

### Port Configuration

The application runs on port 7860 (Hugging Face Spaces default).

## Local Development

```bash
npm install
npm run dev
```

The application will be available at http://localhost:3000
# Deployment trigger
# Rebuild trigger - Mon May 11 10:31:29 PST 2026
