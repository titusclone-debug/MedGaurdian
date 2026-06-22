#!/bin/bash
# MedGuardian — Quick Start Script
# The Institutional Nervous System for Hospital Administration

set -e

echo "🏥 MedGuardian — Quick Start"
echo "================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required"
    exit 1
fi

# Check Node
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required"
    exit 1
fi

echo -e "${BLUE}Step 1: Setting up Backend...${NC}"
cd backend
python3 -m venv venv 2>/dev/null || true
source venv/bin/activate 2>/dev/null || true
pip install -r requirements.txt -q 2>/dev/null || pip install --break-system-packages -r requirements.txt -q
echo -e "${GREEN}✅ Backend dependencies installed${NC}"

echo ""
echo -e "${BLUE}Step 2: Seeding database...${NC}"
python3 scripts/seed_data.py
python3 scripts/seed_regulations.py
echo -e "${GREEN}✅ Database and vector store seeded with sample data${NC}"

echo ""
echo -e "${BLUE}Step 3: Starting Backend (port 8000)...${NC}"
cd ..
cd backend
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..
echo -e "${GREEN}✅ Backend running (PID: $BACKEND_PID)${NC}"

echo ""
echo -e "${BLUE}Step 4: Setting up Frontend...${NC}"
cd frontend
npm install -q 2>/dev/null
echo -e "${GREEN}✅ Frontend dependencies installed${NC}"

echo ""
echo -e "${BLUE}Step 5: Starting Frontend (port 3000)...${NC}"
npm run dev &
FRONTEND_PID=$!
cd ..
echo -e "${GREEN}✅ Frontend running (PID: $FRONTEND_PID)${NC}"

echo ""
echo "================================"
echo -e "${GREEN}🏥 MedGuardian is running!${NC}"
echo ""
echo -e "   Frontend:  ${BLUE}http://localhost:3000${NC}"
echo -e "   Backend:   ${BLUE}http://localhost:8000${NC}"
echo -e "   API Docs:  ${BLUE}http://localhost:8000/docs${NC}"
echo ""
echo -e "${YELLOW}Use credentials issued through the approved bootstrap process.${NC}"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for interrupt
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
