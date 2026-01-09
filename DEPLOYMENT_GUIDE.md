# AI Audit Platform - Complete Deployment Guide

> **Version**: 1.0.0
> **Last Updated**: January 2026
> **Target Audience**: DevOps Engineers, System Administrators, Full-Stack Developers
> **Estimated Read Time**: 30 minutes (Quick Start: 5 minutes)

---

## Table of Contents

1. [Quick Start (5 minutes)](#quick-start-5-minutes)
2. [Development Setup](#development-setup)
3. [Production Deployment](#production-deployment)
4. [Environment Variables](#environment-variables)
5. [Health Checks & Monitoring](#health-checks--monitoring)
6. [Troubleshooting Guide](#troubleshooting-guide)
7. [Advanced Configuration](#advanced-configuration)
8. [Rollback Procedures](#rollback-procedures)

---

## Quick Start (5 minutes)

### Prerequisites Check

\`\`\`bash
# Verify you have these installed
node --version        # v18+
npm --version         # v9+
python --version      # 3.11+
git --version         # any recent version
\`\`\`

### 1. Clone Repository

\`\`\`bash
# Clone the repository
git clone https://github.com/your-org/ai-audit-platform.git
cd ai-audit-platform

# Create a working branch for deployment
git checkout -b deployment/production
\`\`\`

### 2. Install Dependencies

\`\`\`bash
# Backend Dependencies
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Verify installation
python -c "import fastapi; print('✅ FastAPI installed')"

cd ..

# Frontend Dependencies
cd frontend
npm install
npm run build
cd ..
\`\`\`

### 3. Configure Environment Variables

\`\`\`bash
# Backend setup
cd backend
cp .env.example .env
nano .env  # Edit with your values

# Verify
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('✅ Environment loaded')"

cd ..

# Frontend setup
cd frontend
cat > .env.local << 'EOF'
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key-here
EOF
cd ..
\`\`\`

### 4. Database Setup

\`\`\`bash
cd backend
python -c "
from src.db.checkpointer import get_checkpointer, setup_checkpoint_tables
checkpointer = get_checkpointer()
checkpointer.setup()
print('✅ PostgreSQL checkpoint tables created/verified')
"
cd ..
\`\`\`

### 5. Start Development Servers

**Terminal 1 - Backend:**
\`\`\`bash
cd backend
source venv/bin/activate
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8080
\`\`\`

**Terminal 2 - Frontend:**
\`\`\`bash
cd frontend
npm run dev
\`\`\`

### 6. Verify Installation

\`\`\`bash
# Check backend health
curl http://localhost:8080/api/health
# Expected: {"status": "healthy", "timestamp": "..."}

# Check frontend
curl -I http://localhost:5173/

# Check database
curl -X GET http://localhost:8080/api/health/db

echo "✅ All systems operational!"
\`\`\`

---

## Development Setup

### Full Development Environment

[Full development setup documentation with prerequisites, Supabase setup, backend/frontend configuration details...]

---

## Production Deployment

### Backend Deployment Options

#### Option A: Docker Container (Recommended)
#### Option B: Systemd Service (Bare Metal)
#### Option C: Cloud Hosting

### Frontend Deployment

#### Build & Static File Serving
#### Nginx Configuration
#### SSL/TLS Setup

---

## Environment Variables

### Backend Environment Variables

**File**: \`backend/.env.production\`

[Complete list of all backend environment variables with descriptions...]

### Frontend Environment Variables

**File**: \`frontend/.env.production\`

[Complete list of all frontend environment variables...]

---

## Health Checks & Monitoring

### Health Check Endpoints
### Monitoring Setup
### Alerting Rules

---

## Troubleshooting Guide

### Common Issues & Solutions

[10+ common issues with detailed solutions...]

---

## Advanced Configuration

### Load Balancing
### Database Connection Pooling
### Caching Strategy
### Monitoring & Observability

---

## Rollback Procedures

### Backend Rollback
### Frontend Rollback
### Database Rollback
### Zero-Downtime Deployment

---

## Final Checklist

[Pre-deployment, post-deployment, and ongoing monitoring checklists...]

---

**Support**: See DEPLOYMENT_CHECKLIST.md for detailed pre/post deployment verification
