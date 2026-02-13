# OCI Cost Manager - Architecture

## 1. System Overview

The OCI Cost Manager follows a modern three-tier architecture with a React frontend, FastAPI backend, and SQLite/PostgreSQL database.

```
┌─────────────────────────────────────────────────────────────────────┐
│                           CLIENT LAYER                               │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    React Frontend (SPA)                      │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │    │
│  │  │Dashboard │ │Resources │ │ Budget   │ │   Reports    │   │    │
│  │  │  Page    │ │  Page    │ │  Page    │ │    Page      │   │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘   │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ REST API (JSON)
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           API LAYER                                  │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                   FastAPI Backend                            │    │
│  │  ┌──────────────────────────────────────────────────────┐   │    │
│  │  │                    API Routes                         │   │    │
│  │  │  /api/v1/tenancies    /api/v1/compartments           │   │    │
│  │  │  /api/v1/resources    /api/v1/costs                  │   │    │
│  │  │  /api/v1/budgets      /api/v1/prices                 │   │    │
│  │  │  /api/v1/reports      /api/v1/health                 │   │    │
│  │  └──────────────────────────────────────────────────────┘   │    │
│  │  ┌──────────────────────────────────────────────────────┐   │    │
│  │  │                    Services                           │   │    │
│  │  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │   │    │
│  │  │  │  OCI Client │ │    Cost     │ │   Budget    │    │   │    │
│  │  │  │   Service   │ │ Calculator  │ │  Validator  │    │   │    │
│  │  │  └─────────────┘ └─────────────┘ └─────────────┘    │   │    │
│  │  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │   │    │
│  │  │  │   Price     │ │  Resource   │ │   Report    │    │   │    │
│  │  │  │  Updater    │ │  Discovery  │ │  Generator  │    │   │    │
│  │  │  └─────────────┘ └─────────────┘ └─────────────┘    │   │    │
│  │  └──────────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
┌─────────────────────┐ ┌─────────────────┐ ┌─────────────────────┐
│   DATA LAYER        │ │  EXTERNAL APIs  │ │      CACHE          │
│ ┌─────────────────┐ │ │ ┌─────────────┐ │ │ ┌─────────────────┐ │
│ │   SQLite /      │ │ │ │  OCI APIs   │ │ │ │   In-Memory     │ │
│ │   PostgreSQL    │ │ │ │ - Identity  │ │ │ │   (Redis opt.)  │ │
│ │                 │ │ │ │ - Database  │ │ │ │                 │ │
│ │ - Tenancies     │ │ │ │ - Compute   │ │ │ │ - Compartments  │ │
│ │ - Compartments  │ │ │ │ - Usage     │ │ │ │ - Resources     │ │
│ │ - Resources     │ │ │ │ - Pricing   │ │ │ │ - Prices        │ │
│ │ - Costs         │ │ │ └─────────────┘ │ │ └─────────────────┘ │
│ │ - Budgets       │ │ └─────────────────┘ └─────────────────────┘
│ │ - Prices        │ │
│ └─────────────────┘ │
└─────────────────────┘
```

## 2. Component Details

### 2.1 Frontend Components

```
src/frontend/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── common/
│   │   │   ├── Navbar.jsx
│   │   │   ├── Sidebar.jsx
│   │   │   ├── LoadingSpinner.jsx
│   │   │   └── ErrorAlert.jsx
│   │   ├── dashboard/
│   │   │   ├── CostSummaryCard.jsx
│   │   │   ├── TopResourcesChart.jsx
│   │   │   ├── CostTrendChart.jsx
│   │   │   └── BudgetHealthCard.jsx
│   │   ├── resources/
│   │   │   ├── CompartmentTree.jsx
│   │   │   ├── ResourceTable.jsx
│   │   │   ├── ResourceFilter.jsx
│   │   │   └── ResourceDetails.jsx
│   │   ├── budget/
│   │   │   ├── BudgetForm.jsx
│   │   │   ├── BudgetList.jsx
│   │   │   ├── BudgetComparison.jsx
│   │   │   └── VarianceIndicator.jsx
│   │   └── reports/
│   │       ├── ReportBuilder.jsx
│   │       ├── CostTable.jsx
│   │       └── ExportButtons.jsx
│   ├── pages/
│   │   ├── Dashboard.jsx
│   │   ├── Resources.jsx
│   │   ├── Budget.jsx
│   │   ├── Reports.jsx
│   │   └── Settings.jsx
│   ├── services/
│   │   ├── api.js
│   │   ├── ociService.js
│   │   └── exportService.js
│   ├── hooks/
│   │   ├── useResources.js
│   │   ├── useCosts.js
│   │   └── useBudgets.js
│   ├── context/
│   │   └── AppContext.jsx
│   ├── utils/
│   │   ├── formatters.js
│   │   └── constants.js
│   ├── App.jsx
│   └── index.jsx
├── package.json
└── vite.config.js
```

### 2.2 Backend Components

```
src/backend/
├── api/
│   ├── __init__.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── tenancies.py
│   │   ├── compartments.py
│   │   ├── resources.py
│   │   ├── costs.py
│   │   ├── budgets.py
│   │   ├── prices.py
│   │   └── reports.py
│   └── dependencies.py
├── services/
│   ├── __init__.py
│   ├── oci_client.py
│   ├── resource_discovery.py
│   ├── cost_calculator.py
│   ├── budget_validator.py
│   ├── price_updater.py
│   └── report_generator.py
├── models/
│   ├── __init__.py
│   ├── tenancy.py
│   ├── compartment.py
│   ├── resource.py
│   ├── cost.py
│   ├── budget.py
│   └── price.py
├── schemas/
│   ├── __init__.py
│   ├── tenancy.py
│   ├── compartment.py
│   ├── resource.py
│   ├── cost.py
│   ├── budget.py
│   └── price.py
├── core/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   └── security.py
├── main.py
└── requirements.txt
```

## 3. API Design

### 3.1 API Endpoints

#### Tenancies
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/tenancies | List all configured tenancies |
| POST | /api/v1/tenancies | Add new tenancy configuration |
| GET | /api/v1/tenancies/{id} | Get tenancy details |
| DELETE | /api/v1/tenancies/{id} | Remove tenancy |

#### Compartments
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/compartments | List compartments (with hierarchy) |
| GET | /api/v1/compartments/{id} | Get compartment details |
| POST | /api/v1/compartments/refresh | Refresh from OCI |

#### Resources
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/resources | List all resources |
| GET | /api/v1/resources?compartment_id=X | Filter by compartment |
| GET | /api/v1/resources?type=oracle_db | Filter by type |
| GET | /api/v1/resources/{id} | Get resource details |
| POST | /api/v1/resources/discover | Trigger resource discovery |

#### Costs
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/costs | Get cost summary |
| GET | /api/v1/costs?period=monthly | Filter by period |
| GET | /api/v1/costs/by-resource | Costs grouped by resource |
| GET | /api/v1/costs/by-compartment | Costs grouped by compartment |
| GET | /api/v1/costs/by-sku | Costs grouped by SKU |
| GET | /api/v1/costs/trends | Cost trends over time |
| POST | /api/v1/costs/calculate | Trigger cost calculation |

#### Budgets
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/budgets | List all budgets |
| POST | /api/v1/budgets | Create new budget |
| GET | /api/v1/budgets/{id} | Get budget details |
| PUT | /api/v1/budgets/{id} | Update budget |
| DELETE | /api/v1/budgets/{id} | Delete budget |
| GET | /api/v1/budgets/{id}/status | Get budget vs actual |

#### Prices
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/prices | List all prices |
| GET | /api/v1/prices?service=database | Filter by service |
| POST | /api/v1/prices/refresh | Update prices from OCI |
| GET | /api/v1/prices/history | Price change history |

#### Reports
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/reports/generate | Generate report |
| GET | /api/v1/reports/export/csv | Export as CSV |
| GET | /api/v1/reports/export/excel | Export as Excel |
| GET | /api/v1/reports/export/pdf | Export as PDF |

### 3.2 Response Formats

**Success Response:**
```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "total": 100,
    "page": 1,
    "per_page": 20
  }
}
```

**Error Response:**
```json
{
  "success": false,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Resource with ID xyz not found",
    "details": { ... }
  }
}
```

## 4. OCI API Integration

### 4.1 Required OCI APIs

| API | Purpose | SDK Module |
|-----|---------|------------|
| Identity | Compartments, Tenancy | `oci.identity` |
| Database | Oracle DB Systems | `oci.database` |
| MySQL | MySQL DB Systems | `oci.mysql` |
| Compute | Instances (SQL Server) | `oci.core` |
| Usage | Cost & Usage data | `oci.usage_api` |
| Pricing | Price List | HTTP (REST) |

### 4.2 OCI SDK Configuration

```python
# config.py
import oci

def get_oci_config(profile_name: str = "DEFAULT"):
    return oci.config.from_file(profile_name=profile_name)

def get_identity_client(config):
    return oci.identity.IdentityClient(config)

def get_database_client(config):
    return oci.database.DatabaseClient(config)

def get_mysql_client(config):
    return oci.mysql.DbSystemClient(config)

def get_compute_client(config):
    return oci.core.ComputeClient(config)

def get_usage_client(config):
    return oci.usage_api.UsageapiClient(config)
```

### 4.3 Price List API Integration

```python
# price_updater.py
import httpx

OCI_PRICE_API = "https://apexapps.oracle.com/pls/apex/cetools/api/v1/products/"

async def fetch_oci_prices(service_name: str = None):
    async with httpx.AsyncClient() as client:
        params = {}
        if service_name:
            params["serviceName"] = service_name
        
        response = await client.get(OCI_PRICE_API, params=params)
        return response.json()
```

## 5. Security Architecture

### 5.1 Credential Management

```
┌─────────────────────────────────────────────────────┐
│                 Credential Flow                      │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────┐    ┌─────────────┐               │
│  │ OCI Config  │───▶│ Environment │               │
│  │   File      │    │  Variables  │               │
│  │ (~/.oci)    │    │             │               │
│  └─────────────┘    └──────┬──────┘               │
│                            │                        │
│                            ▼                        │
│                    ┌───────────────┐               │
│                    │   Backend     │               │
│                    │   Service     │               │
│                    └───────┬───────┘               │
│                            │                        │
│                            ▼                        │
│                    ┌───────────────┐               │
│                    │   OCI SDK     │               │
│                    │   Client      │               │
│                    └───────────────┘               │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 5.2 Security Measures

1. **API Key Storage**: OCI config file on server (not in database)
2. **No Credential Exposure**: Keys never sent to frontend
3. **CORS Configuration**: Restricted to frontend origin
4. **Rate Limiting**: Prevent API abuse
5. **Input Validation**: All inputs sanitized

## 6. Deployment Architecture

### 6.1 Development Setup

```
┌─────────────────────────────────────────────────────┐
│               Local Development                      │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────┐        ┌──────────────┐         │
│  │   Frontend   │        │   Backend    │         │
│  │   (Vite)     │◀──────▶│  (Uvicorn)   │         │
│  │   :3000      │        │   :8000      │         │
│  └──────────────┘        └──────┬───────┘         │
│                                 │                   │
│                          ┌──────▼───────┐         │
│                          │   SQLite     │         │
│                          │   (local)    │         │
│                          └──────────────┘         │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 6.2 Production Setup

```
┌─────────────────────────────────────────────────────┐
│               Production (Docker)                    │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────┐     ┌──────────────────────┐    │
│  │   Nginx      │     │    Docker Network     │    │
│  │   (Reverse   │     │                       │    │
│  │    Proxy)    │─────┤  ┌──────────────┐    │    │
│  │   :443       │     │  │  Frontend    │    │    │
│  └──────────────┘     │  │  Container   │    │    │
│                       │  └──────────────┘    │    │
│                       │                       │    │
│                       │  ┌──────────────┐    │    │
│                       │  │  Backend     │    │    │
│                       │  │  Container   │    │    │
│                       │  └──────┬───────┘    │    │
│                       │         │            │    │
│                       │  ┌──────▼───────┐    │    │
│                       │  │  PostgreSQL  │    │    │
│                       │  │  Container   │    │    │
│                       │  └──────────────┘    │    │
│                       └──────────────────────┘    │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## 7. Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Frontend | React | 18.x |
| UI Components | Tailwind CSS | 3.x |
| Charts | Recharts | 2.x |
| State Management | React Context | - |
| HTTP Client | Axios | 1.x |
| Build Tool | Vite | 5.x |
| Backend | FastAPI | 0.109.x |
| ORM | SQLAlchemy | 2.x |
| Database | SQLite / PostgreSQL | 3.x / 15.x |
| OCI SDK | oci-python-sdk | 2.x |
| HTTP Client | httpx | 0.26.x |
| Task Queue | (Optional) Celery | 5.x |

## 8. Error Handling Strategy

```python
# Exception hierarchy
class OCICostManagerError(Exception):
    """Base exception"""
    pass

class OCIConnectionError(OCICostManagerError):
    """Failed to connect to OCI"""
    pass

class ResourceNotFoundError(OCICostManagerError):
    """Resource not found"""
    pass

class BudgetExceededError(OCICostManagerError):
    """Budget threshold exceeded"""
    pass

class PriceUpdateError(OCICostManagerError):
    """Failed to update prices"""
    pass
```

## 9. Logging Strategy

```python
# Logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard"
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "logs/app.log",
            "level": "DEBUG",
            "formatter": "detailed"
        }
    },
    "loggers": {
        "oci_cost_manager": {
            "handlers": ["console", "file"],
            "level": "DEBUG"
        }
    }
}
```
