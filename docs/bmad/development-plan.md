# OCI Cost Manager - Development Plan

## 1. Project Timeline Overview

**Total Duration**: 6-8 weeks (Phase 1 MVP)

```
Week 1-2: Foundation & Core Backend
Week 3-4: OCI Integration & Cost Engine
Week 5-6: Frontend Development
Week 7-8: Testing, Polish & Documentation
```

## 2. Sprint Breakdown

### Sprint 1: Foundation (Week 1)

#### Goals
- Set up development environment
- Create project structure
- Implement database models
- Basic API scaffolding

#### Tasks

| ID | Task | Priority | Effort | Status |
|----|------|----------|--------|--------|
| S1-01 | Set up Python virtual environment | High | 1h | Pending |
| S1-02 | Install backend dependencies (FastAPI, SQLAlchemy, OCI SDK) | High | 1h | Pending |
| S1-03 | Create database models (Tenancy, Compartment, Resource) | High | 4h | Pending |
| S1-04 | Create database models (Budget, Cost, Price) | High | 4h | Pending |
| S1-05 | Set up SQLite database connection | High | 2h | Pending |
| S1-06 | Create Pydantic schemas for API | High | 4h | Pending |
| S1-07 | Implement basic FastAPI app structure | High | 2h | Pending |
| S1-08 | Create API route stubs | Medium | 2h | Pending |
| S1-09 | Set up logging configuration | Medium | 1h | Pending |
| S1-10 | Create configuration management | High | 2h | Pending |

**Deliverables**:
- Working FastAPI server
- Database schema created
- API endpoints returning mock data

---

### Sprint 2: OCI Integration (Week 2)

#### Goals
- Implement OCI SDK integration
- Resource discovery services
- Compartment hierarchy

#### Tasks

| ID | Task | Priority | Effort | Status |
|----|------|----------|--------|--------|
| S2-01 | Create OCI client service | High | 4h | Pending |
| S2-02 | Implement tenancy configuration | High | 2h | Pending |
| S2-03 | Implement compartment discovery | High | 4h | Pending |
| S2-04 | Build compartment hierarchy tree | High | 3h | Pending |
| S2-05 | Implement Oracle DB discovery | High | 4h | Pending |
| S2-06 | Implement MySQL DB discovery | High | 4h | Pending |
| S2-07 | Implement compute instance discovery | High | 4h | Pending |
| S2-08 | Create resource caching mechanism | Medium | 3h | Pending |
| S2-09 | Add error handling for OCI API calls | High | 2h | Pending |
| S2-10 | Write unit tests for discovery services | Medium | 4h | Pending |

**Deliverables**:
- OCI connection working
- Compartments discoverable
- Resources discoverable by type

---

### Sprint 3: Cost Engine (Week 3)

#### Goals
- Implement Usage API integration
- Cost calculation service
- Price list integration

#### Tasks

| ID | Task | Priority | Effort | Status |
|----|------|----------|--------|--------|
| S3-01 | Implement Usage API client | High | 4h | Pending |
| S3-02 | Create cost query builder | High | 4h | Pending |
| S3-03 | Implement cost aggregation by resource | High | 4h | Pending |
| S3-04 | Implement cost aggregation by compartment | High | 3h | Pending |
| S3-05 | Implement cost aggregation by SKU | High | 3h | Pending |
| S3-06 | Create price list API client | High | 3h | Pending |
| S3-07 | Implement price caching | Medium | 2h | Pending |
| S3-08 | Create price update scheduler | Medium | 3h | Pending |
| S3-09 | Build cost trends calculation | Medium | 4h | Pending |
| S3-10 | Write unit tests for cost engine | Medium | 4h | Pending |

**Deliverables**:
- Costs calculated per resource
- Price list synced from OCI
- Historical cost data available

---

### Sprint 4: Budget Module (Week 4)

#### Goals
- Implement budget management
- Budget validation logic
- Alerts and thresholds

#### Tasks

| ID | Task | Priority | Effort | Status |
|----|------|----------|--------|--------|
| S4-01 | Create budget CRUD API | High | 4h | Pending |
| S4-02 | Implement budget validation service | High | 4h | Pending |
| S4-03 | Create actual vs budget comparison | High | 4h | Pending |
| S4-04 | Implement variance calculation | High | 2h | Pending |
| S4-05 | Create budget status indicators | High | 2h | Pending |
| S4-06 | Implement budget forecasting | Medium | 4h | Pending |
| S4-07 | Create alert threshold logic | Medium | 3h | Pending |
| S4-08 | Implement compartment-scoped budgets | Medium | 3h | Pending |
| S4-09 | Write unit tests for budget module | Medium | 4h | Pending |
| S4-10 | Create API documentation | Medium | 2h | Pending |

**Deliverables**:
- Budget CRUD operations
- Budget vs actual comparison working
- Forecast based on burn rate

---

### Sprint 5: Frontend Foundation (Week 5)

#### Goals
- Set up React project
- Create core components
- Implement navigation

#### Tasks

| ID | Task | Priority | Effort | Status |
|----|------|----------|--------|--------|
| S5-01 | Initialize React project with Vite | High | 2h | Pending |
| S5-02 | Set up Tailwind CSS | High | 1h | Pending |
| S5-03 | Create app layout (Navbar, Sidebar) | High | 4h | Pending |
| S5-04 | Implement React Router navigation | High | 2h | Pending |
| S5-05 | Create API service layer | High | 3h | Pending |
| S5-06 | Create Dashboard page skeleton | High | 3h | Pending |
| S5-07 | Create Resources page skeleton | High | 3h | Pending |
| S5-08 | Create Budget page skeleton | High | 3h | Pending |
| S5-09 | Create Reports page skeleton | High | 3h | Pending |
| S5-10 | Implement loading states and error handling | High | 3h | Pending |

**Deliverables**:
- React app running
- Navigation working
- Page skeletons in place

---

### Sprint 6: Frontend Features (Week 6)

#### Goals
- Build interactive components
- Implement data visualization
- Complete all pages

#### Tasks

| ID | Task | Priority | Effort | Status |
|----|------|----------|--------|--------|
| S6-01 | Create CompartmentTree component | High | 4h | Pending |
| S6-02 | Create ResourceTable with filtering | High | 4h | Pending |
| S6-03 | Create CostSummaryCard component | High | 3h | Pending |
| S6-04 | Implement TopResourcesChart (Recharts) | High | 4h | Pending |
| S6-05 | Implement CostTrendChart | High | 4h | Pending |
| S6-06 | Create BudgetForm component | High | 3h | Pending |
| S6-07 | Create BudgetComparison component | High | 4h | Pending |
| S6-08 | Implement VarianceIndicator | High | 2h | Pending |
| S6-09 | Create report export functionality | High | 4h | Pending |
| S6-10 | Implement Settings page | Medium | 3h | Pending |

**Deliverables**:
- All components functional
- Charts rendering data
- Export working

---

### Sprint 7: Integration & Testing (Week 7)

#### Goals
- End-to-end integration
- Testing and bug fixes
- Performance optimization

#### Tasks

| ID | Task | Priority | Effort | Status |
|----|------|----------|--------|--------|
| S7-01 | End-to-end integration testing | High | 8h | Pending |
| S7-02 | Fix integration bugs | High | 8h | Pending |
| S7-03 | Performance testing | Medium | 4h | Pending |
| S7-04 | Optimize API response times | Medium | 4h | Pending |
| S7-05 | Optimize frontend bundle size | Medium | 3h | Pending |
| S7-06 | Add frontend unit tests | Medium | 4h | Pending |
| S7-07 | Security review | High | 4h | Pending |
| S7-08 | Fix security issues | High | 4h | Pending |
| S7-09 | Cross-browser testing | Medium | 3h | Pending |
| S7-10 | Responsive design fixes | Medium | 3h | Pending |

**Deliverables**:
- All tests passing
- No critical bugs
- Acceptable performance

---

### Sprint 8: Documentation & Deployment (Week 8)

#### Goals
- Complete documentation
- Set up deployment
- Final polish

#### Tasks

| ID | Task | Priority | Effort | Status |
|----|------|----------|--------|--------|
| S8-01 | Write installation guide | High | 3h | Pending |
| S8-02 | Write user documentation | High | 4h | Pending |
| S8-03 | Write API documentation (OpenAPI) | High | 3h | Pending |
| S8-04 | Create Dockerfile for backend | High | 2h | Pending |
| S8-05 | Create Dockerfile for frontend | High | 2h | Pending |
| S8-06 | Create docker-compose.yml | High | 2h | Pending |
| S8-07 | Set up CI/CD pipeline | Medium | 4h | Pending |
| S8-08 | Create deployment scripts | Medium | 3h | Pending |
| S8-09 | Final UI polish | Medium | 4h | Pending |
| S8-10 | Create demo/walkthrough video | Low | 3h | Pending |

**Deliverables**:
- Complete documentation
- Docker deployment ready
- MVP released

---

## 3. Technical Milestones

| Milestone | Target Date | Criteria |
|-----------|-------------|----------|
| M1: Backend API Ready | End of Week 2 | All API endpoints functional |
| M2: OCI Integration Complete | End of Week 3 | Resources and costs discoverable |
| M3: Cost Engine Working | End of Week 4 | Accurate cost calculations |
| M4: Frontend MVP | End of Week 6 | All pages functional |
| M5: Integration Complete | End of Week 7 | End-to-end flow working |
| M6: Production Ready | End of Week 8 | Documented and deployable |

## 4. Risk Management

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| OCI API rate limits | Medium | High | Implement caching, request throttling |
| Complex compartment hierarchies | Medium | Medium | Test with real-world structures |
| Price list API changes | Low | Medium | Version price list parsing |
| Large data volumes | Medium | High | Implement pagination, lazy loading |
| Browser compatibility | Low | Medium | Test early on multiple browsers |

## 5. Definition of Done

A feature is considered "Done" when:

1. ✅ Code is written and follows style guidelines
2. ✅ Unit tests pass with >80% coverage
3. ✅ Integration tests pass
4. ✅ Code reviewed and approved
5. ✅ Documentation updated
6. ✅ No critical or high-severity bugs
7. ✅ Works on all supported browsers
8. ✅ Accessible (basic a11y compliance)

## 6. Development Environment Setup

### Prerequisites
```bash
# Required software
- Python 3.11+
- Node.js 20+
- Git
- OCI CLI configured (~/.oci/config)
```

### Backend Setup
```bash
cd src/backend
python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend Setup
```bash
cd src/frontend
npm install
npm run dev
```

## 7. Code Quality Standards

### Python (Backend)
- Formatter: Black
- Linter: Ruff
- Type hints required
- Docstrings for public functions

### JavaScript (Frontend)
- Formatter: Prettier
- Linter: ESLint
- PropTypes or TypeScript
- JSDoc for complex functions

## 8. Git Workflow

```
main (production)
  └── develop (integration)
        ├── feature/S1-01-setup-environment
        ├── feature/S2-05-oracle-db-discovery
        └── bugfix/cost-calculation-error
```

### Branch Naming
- `feature/SPRINT-TASK-description`
- `bugfix/description`
- `hotfix/critical-issue`

### Commit Messages
```
feat(backend): add OCI client service
fix(frontend): correct cost calculation display
docs: update API documentation
test: add unit tests for budget service
```

## 9. Phase 2 Roadmap (Future)

| Feature | Description | Priority |
|---------|-------------|----------|
| Multi-cloud | Add AWS/Azure support | Medium |
| AI Recommendations | Cost optimization suggestions | Medium |
| Scheduled Reports | Email reports on schedule | Low |
| Custom Tags | Filter by OCI tags | Medium |
| Role-Based Access | Multi-user with permissions | Medium |
| Mobile App | React Native companion | Low |
