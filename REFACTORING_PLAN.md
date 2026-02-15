# EPL App - Comprehensive Refactoring Plan

## Executive Summary

This document outlines a comprehensive refactoring plan to modernize the FPL AI Pro codebase, improve maintainability, and prepare for production scaling.

## Current State Analysis

### Critical Issues Identified

1. **Code Duplication Crisis**
   - 29 Python files scattered in root directory
   - 27 Python files in `/functions` directory (many duplicates)
   - Duplicate files differ between locations (maintenance nightmare)
   - Three separate `/src` directories: root, `/backend/src`, `/web/src`

2. **Dependency Management Chaos**
   - 8 separate requirements files:
     - requirements.txt
     - requirements_local.txt
     - requirements_cloud.txt
     - requirements_ai.txt
     - requirements_ai_simple.txt
     - requirements_production.txt
     - requirements_firebase.txt
     - requirements_gemini.txt
     - functions/requirements.txt
   - Version conflicts and redundancy
   - No clear dependency groups

3. **Multiple API Implementations**
   - `api_production.py` (1,389 lines) - Current production
   - `enhanced_api_production.py` (959 lines) - Enhanced with xG/xA
   - `api_enhanced_final.py` (570 lines)
   - `api_ai_enhanced.py` (449 lines)
   - `api_with_ai.py` (425 lines)
   - `api_lightweight.py` (184 lines)
   - Unclear which version is canonical

4. **Outdated Dependencies**
   - Next.js 14.0.0 (current: 15.x)
   - FastAPI 0.104.1 (current: 0.115.x)
   - NumPy 1.26.2 (current: 2.2.x)
   - Pandas 2.1.3 (current: 2.2.x)

5. **Poor Project Structure**
   - No clear separation between backend/frontend/functions
   - Test files scattered everywhere
   - Multiple Dockerfiles with unclear purposes
   - Documentation fragmented across 15+ files

## Proposed New Structure

```
EPL_app/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # Single FastAPI app entry point
│   │   ├── config.py          # Environment & configuration
│   │   ├── api/               # API route modules
│   │   │   ├── __init__.py
│   │   │   ├── players.py     # Player endpoints
│   │   │   ├── predictions.py # Prediction endpoints
│   │   │   ├── teams.py       # Team optimization
│   │   │   └── payments.py    # PayStack integration
│   │   ├── services/          # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── prediction_service.py
│   │   │   ├── data_service.py
│   │   │   └── ml_service.py
│   │   ├── models/            # ML models
│   │   │   ├── __init__.py
│   │   │   ├── random_forest.py
│   │   │   ├── cnn_model.py
│   │   │   └── ensemble.py
│   │   ├── utils/             # Utilities
│   │   │   ├── __init__.py
│   │   │   ├── cache.py
│   │   │   ├── logging.py
│   │   │   └── validators.py
│   │   └── schemas/           # Pydantic models
│   │       ├── __init__.py
│   │       ├── player.py
│   │       └── prediction.py
│   ├── tests/                 # Backend tests
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_api/
│   │   ├── test_services/
│   │   └── test_models/
│   ├── Dockerfile             # Production Docker
│   ├── pyproject.toml         # Modern Python packaging
│   └── README.md
│
├── frontend/                   # Next.js frontend
│   ├── app/                   # Next.js 15 app directory
│   │   ├── layout.js
│   │   ├── page.js
│   │   └── predictions/
│   ├── components/            # React components
│   │   ├── ui/               # UI components
│   │   ├── features/         # Feature components
│   │   └── layout/           # Layout components
│   ├── lib/                  # Frontend utilities
│   │   ├── api.js            # API client
│   │   └── utils.js
│   ├── public/               # Static assets
│   ├── package.json
│   ├── next.config.js
│   └── README.md
│
├── functions/                 # Firebase Cloud Functions
│   ├── main.py               # Cloud Function entry point
│   ├── requirements.txt      # Function-specific deps
│   └── README.md
│
├── docs/                      # Consolidated documentation
│   ├── README.md             # Main documentation
│   ├── API.md                # API documentation
│   ├── DEPLOYMENT.md         # Deployment guide
│   ├── DEVELOPMENT.md        # Development setup
│   └── ARCHITECTURE.md       # System architecture
│
├── scripts/                   # Utility scripts
│   ├── deploy_backend.sh
│   ├── deploy_frontend.sh
│   └── setup_dev.sh
│
├── .github/                   # CI/CD
│   └── workflows/
│       ├── backend-ci.yml
│       ├── frontend-ci.yml
│       └── deploy.yml
│
├── docker-compose.yml         # Local development
├── .env.example
├── .gitignore
└── README.md
```

## Refactoring Tasks

### Phase 1: Foundation (Priority: Critical)

#### Task 1: Create New Directory Structure ✅
- Create the new directory structure
- Set up proper Python packages with `__init__.py`
- Create configuration management

#### Task 2: Consolidate API Files
- Analyze all API versions
- Merge best features into single `backend/app/main.py`
- Keep xG/xA analytics from `enhanced_api_production.py`
- Preserve Gemini AI integration
- Split into logical route modules

#### Task 3: Modernize Dependency Management
- Create `backend/pyproject.toml` with Poetry or setuptools
- Define dependency groups:
  - `[tool.poetry.dependencies]` - Production
  - `[tool.poetry.group.dev.dependencies]` - Development
  - `[tool.poetry.group.ml.dependencies]` - ML models
  - `[tool.poetry.group.test.dependencies]` - Testing
- Update to latest compatible versions
- Remove all old requirements*.txt files

### Phase 2: Backend Refactoring (Priority: High)

#### Task 4: Reorganize Python Modules
- Move files from root to proper backend structure:
  - API files → `backend/app/api/`
  - ML models → `backend/app/models/`
  - Utilities → `backend/app/utils/`
  - Services → `backend/app/services/`
- Remove duplicates in functions directory
- Update imports throughout codebase

#### Task 5: Implement Proper Configuration
- Create `backend/app/config.py` with Pydantic Settings
- Validate environment variables
- Type-safe configuration access
- Clear documentation of all env vars

#### Task 6: Add Comprehensive Error Handling
- Structured logging with contextvars
- Custom exception classes
- Proper error responses
- Request ID tracking

#### Task 7: Improve ML Pipeline
- Consolidate model implementations
- Add model versioning
- Implement model registry
- Add prediction explanations

### Phase 3: Frontend Modernization (Priority: High)

#### Task 8: Upgrade Next.js
- Upgrade to Next.js 15.x
- Update React 18 → 19 (if stable)
- Upgrade TailwindCSS to v4
- Update all frontend dependencies

#### Task 9: Improve Component Organization
- Organize components by feature
- Create reusable UI components
- Implement proper TypeScript (if desired)
- Add component documentation

#### Task 10: Optimize Build & Performance
- Implement proper code splitting
- Optimize images with Next.js Image
- Add caching strategies
- Improve SEO

### Phase 4: DevOps & Infrastructure (Priority: Medium)

#### Task 11: Consolidate Docker Configuration
- Single production `Dockerfile` for backend
- Multi-stage build for optimization
- Docker Compose for local development
- Clear documentation

#### Task 12: Improve CI/CD
- Comprehensive GitHub Actions workflows
- Automated testing on PR
- Automated deployment
- Environment-specific deployments

#### Task 13: Add Monitoring & Observability
- Structured logging
- Performance monitoring
- Error tracking (Sentry/similar)
- Health check endpoints

### Phase 5: Testing & Quality (Priority: Medium)

#### Task 14: Backend Testing
- Unit tests for all services
- Integration tests for API
- ML model tests
- >80% code coverage target

#### Task 15: Frontend Testing
- Component tests with Jest
- E2E tests with Playwright
- Visual regression tests
- Accessibility tests

#### Task 16: Code Quality Tools
- Add pre-commit hooks
- Configure Black for Python formatting
- Add ESLint/Prettier for frontend
- Type checking with mypy

### Phase 6: Documentation (Priority: Medium)

#### Task 17: Consolidate Documentation
- Merge overlapping docs:
  - DEPLOYMENT_*.md → docs/DEPLOYMENT.md
  - FIREBASE_*.md → docs/DEPLOYMENT.md
  - *_GUIDE.md → docs/
- API documentation with OpenAPI
- Architecture diagrams
- Development setup guide

#### Task 18: Add Code Documentation
- Docstrings for all functions
- Type hints throughout
- README for each major module
- Contributing guide

## Migration Strategy

### Step-by-Step Migration

1. **Week 1: Foundation**
   - Create new directory structure alongside existing
   - Set up pyproject.toml
   - Migrate configuration management
   - No breaking changes yet

2. **Week 2: Backend Migration**
   - Consolidate API files into new structure
   - Move models and services
   - Update imports
   - Test thoroughly

3. **Week 3: Frontend Update**
   - Upgrade Next.js and dependencies
   - Reorganize components
   - Test all functionality

4. **Week 4: Testing & Documentation**
   - Add comprehensive tests
   - Update documentation
   - Code review and refinement

5. **Week 5: Deployment**
   - Update Docker configuration
   - Test deployment pipeline
   - Deploy to staging
   - Deploy to production

### Risk Mitigation

- Keep old code until new version is fully tested
- Use feature flags for gradual rollout
- Maintain backward compatibility where possible
- Comprehensive testing at each step
- Git branches for each major change

## Success Metrics

- [ ] Single source of truth for each module (no duplicates)
- [ ] All dependencies in one place (pyproject.toml)
- [ ] >80% test coverage
- [ ] Zero linting errors
- [ ] Build time <2 minutes
- [ ] API response time <200ms (p95)
- [ ] Deployment time <5 minutes
- [ ] Documentation complete and accurate

## Timeline

- **Phase 1-2**: 2 weeks (Foundation + Backend)
- **Phase 3**: 1 week (Frontend)
- **Phase 4**: 1 week (DevOps)
- **Phase 5-6**: 1 week (Testing + Docs)
- **Total**: ~5-6 weeks for complete refactoring

## Dependencies to Preserve

Critical integrations that must be maintained:
- Gemini AI integration for predictions
- xG/xA analytics from enhanced API
- PayStack payment integration
- Firebase deployment setup
- Multi-model ML ensemble (RandomForest + CNN + Gemini)

## Files to Remove

After successful migration:
- All root-level `*.py` files except `run.py` (if needed)
- All `requirements_*.txt` files
- Duplicate files in `/functions`
- Old documentation files
- Multiple Dockerfiles (keep one optimized version)

## Next Steps

1. Review and approve this plan
2. Create feature branch: `feature/major-refactoring`
3. Begin Phase 1 implementation
4. Regular check-ins and reviews
5. Testing and validation
6. Gradual deployment

---

**Created**: 2026-02-15
**Status**: Pending Approval
**Estimated Effort**: 5-6 weeks
**Risk Level**: Medium (mitigated by careful migration strategy)
