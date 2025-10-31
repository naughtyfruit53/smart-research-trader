# Smart Research Trader

AI-powered stock research and trading signals platform combining fundamentals, technicals, news sentiment, and machine learning.

**⚠️ Disclaimer: For research and education only. Not investment advice. Check local regulations before trading.**

## 📋 Overview

Smart Research Trader is a comprehensive platform for:
- Fundamental analysis (ROE/ROCE, growth, leverage, valuation)
- Technical indicators (trend, momentum, volatility, volume)
- News sentiment analysis with FinBERT
- AI-driven long/short signals using LightGBM
- Backtesting with transaction costs and risk metrics
- Interactive UI with signal explainability (SHAP)

## 🏗️ Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **PostgreSQL** - Primary database
- **Redis** - Caching and task queue
- **Celery** - Background task processing (planned)
- **uvicorn** - ASGI server

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Styling
- **shadcn/ui** - Component library

### Infrastructure
- **Docker & Docker Compose** - Containerization
- **GitHub Actions** - CI/CD pipeline
- **nginx** - Production serving (planned)

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Git

### Development Setup

1. Clone the repository:
```bash
git clone https://github.com/naughtyfruit53/smart-research-trader.git
cd smart-research-trader
```

2. Start all services:
```bash
docker compose up --build
```

Or use the convenience script:
```bash
./infra/scripts/dev_up.sh
```

3. Access the application:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### Local Development (without Docker)

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install ruff black mypy pytest
uvicorn src.api.main:app --reload
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Type Check
```bash
cd frontend
npm run type-check
npm run build
```

### Linting
```bash
# Backend
cd backend
ruff check .
black --check .
mypy src tests

# Frontend
cd frontend
npm run lint
```

## 📁 Project Structure

```
smart-research-trader/
├── backend/
│   ├── src/
│   │   ├── core/          # Config, logging, utilities
│   │   └── api/           # FastAPI app and routes
│   ├── tests/             # Backend tests
│   ├── Dockerfile
│   ├── celeryworker.dockerfile
│   ├── requirements.txt
│   └── pyproject.toml     # Python tool configs
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components
│   │   └── lib/           # Utilities and API client
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── infra/
│   └── scripts/           # Development scripts
├── .github/
│   └── workflows/         # CI/CD workflows
├── docker-compose.yml
└── README.md
```

## 🔧 Configuration

### Environment Variables

Backend (`.env` in `backend/`):
```bash
APP_ENV=development
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["http://localhost:5173"]
LOG_LEVEL=INFO
```

Frontend:
```bash
VITE_API_BASE=http://localhost:8000
```

## 🚦 CI/CD

The project uses GitHub Actions for continuous integration:
1. **Python Lint & Test** - Runs ruff, black, mypy, and pytest
2. **Frontend TypeCheck & Build** - Validates TypeScript and builds
3. **Docker Build** - Builds backend and frontend images

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## ⚠️ Important Disclaimers

- This software is for **research and educational purposes only**
- **Not financial or investment advice**
- Past performance does not guarantee future results
- Trading involves substantial risk of loss
- Consult with licensed financial advisors before making investment decisions
- Check and comply with local regulations (e.g., SEBI in India)

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure CI passes
5. Submit a pull request

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation
- Review API docs at `/docs` endpoint
