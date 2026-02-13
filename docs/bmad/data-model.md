# OCI Cost Manager - Data Model

## 1. Overview

This document defines the data entities, relationships, and database schema for the OCI Cost Manager application.

## 2. Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│    Tenancy      │       │   Compartment   │       │    Resource     │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │──────<│ id (PK)         │──────<│ id (PK)         │
│ ocid            │       │ tenancy_id (FK) │       │ compartment_id  │
│ name            │       │ parent_id (FK)  │       │ ocid            │
│ home_region     │       │ ocid            │       │ name            │
│ config_profile  │       │ name            │       │ resource_type   │
│ created_at      │       │ description     │       │ shape           │
│ updated_at      │       │ lifecycle_state │       │ status          │
└─────────────────┘       │ created_at      │       │ details (JSON)  │
                          └─────────────────┘       │ created_at      │
                                                    └─────────────────┘
                                                            │
                                                            │
┌─────────────────┐       ┌─────────────────┐       ┌───────▼─────────┐
│     Budget      │       │   CostRecord    │       │    UsageData    │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │       │ id (PK)         │
│ name            │       │ resource_id(FK) │       │ resource_id(FK) │
│ compartment_id  │       │ sku_name        │       │ date            │
│ amount          │       │ sku_part_number │       │ quantity        │
│ period_type     │──────>│ unit_price      │<──────│ unit            │
│ start_date      │       │ quantity        │       │ cost            │
│ end_date        │       │ cost            │       │ currency        │
│ alert_threshold │       │ period_start    │       │ created_at      │
│ created_at      │       │ period_end      │       └─────────────────┘
│ updated_at      │       │ created_at      │
└─────────────────┘       └─────────────────┘

┌─────────────────┐       ┌─────────────────┐
│   PriceList     │       │   PriceHistory  │
├─────────────────┤       ├─────────────────┤
│ id (PK)         │──────<│ id (PK)         │
│ sku_part_number │       │ price_id (FK)   │
│ service_name    │       │ unit_price      │
│ product_name    │       │ effective_date  │
│ unit_price      │       │ created_at      │
│ currency        │       └─────────────────┘
│ unit            │
│ region          │
│ last_updated    │
│ created_at      │
└─────────────────┘
```

## 3. Entity Definitions

### 3.1 Tenancy
Represents an OCI tenancy (account) with its configuration.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | UUID | Primary key | NOT NULL, UNIQUE |
| ocid | VARCHAR(255) | OCI tenancy OCID | NOT NULL, UNIQUE |
| name | VARCHAR(255) | Display name | NOT NULL |
| home_region | VARCHAR(50) | Home region identifier | NOT NULL |
| config_profile | VARCHAR(100) | OCI config profile name | NOT NULL |
| created_at | TIMESTAMP | Record creation time | NOT NULL |
| updated_at | TIMESTAMP | Last update time | NOT NULL |

### 3.2 Compartment
Represents an OCI compartment with hierarchical structure.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | UUID | Primary key | NOT NULL, UNIQUE |
| tenancy_id | UUID | Foreign key to Tenancy | NOT NULL |
| parent_id | UUID | Self-reference for hierarchy | NULLABLE |
| ocid | VARCHAR(255) | OCI compartment OCID | NOT NULL |
| name | VARCHAR(255) | Compartment name | NOT NULL |
| description | TEXT | Compartment description | NULLABLE |
| lifecycle_state | VARCHAR(50) | ACTIVE, DELETED, etc. | NOT NULL |
| created_at | TIMESTAMP | Record creation time | NOT NULL |

### 3.3 Resource
Represents a database or compute resource.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | UUID | Primary key | NOT NULL, UNIQUE |
| compartment_id | UUID | Foreign key to Compartment | NOT NULL |
| ocid | VARCHAR(255) | OCI resource OCID | NOT NULL, UNIQUE |
| name | VARCHAR(255) | Resource display name | NOT NULL |
| resource_type | ENUM | ORACLE_DB, MYSQL, SQL_SERVER, AUTONOMOUS_DB | NOT NULL |
| shape | VARCHAR(100) | Compute shape | NULLABLE |
| status | VARCHAR(50) | AVAILABLE, RUNNING, etc. | NOT NULL |
| details | JSON | Additional resource-specific info | NULLABLE |
| created_at | TIMESTAMP | Record creation time | NOT NULL |

**Resource Details JSON Schema:**
```json
{
  "oracle_db": {
    "edition": "ENTERPRISE_EDITION",
    "version": "19.0.0.0",
    "ocpus": 4,
    "storage_gb": 1024,
    "node_count": 1
  },
  "mysql": {
    "version": "8.0.32",
    "heatwave_enabled": true,
    "storage_gb": 500
  },
  "sql_server": {
    "image_name": "SQL Server 2022 Enterprise",
    "memory_gb": 72,
    "ocpus": 4
  }
}
```

### 3.4 Budget
Represents a budget allocation.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | UUID | Primary key | NOT NULL, UNIQUE |
| name | VARCHAR(255) | Budget name | NOT NULL |
| compartment_id | UUID | Optional compartment scope | NULLABLE |
| amount | DECIMAL(15,2) | Budget amount | NOT NULL |
| period_type | ENUM | MONTHLY, YEARLY | NOT NULL |
| start_date | DATE | Budget start date | NOT NULL |
| end_date | DATE | Budget end date | NULLABLE |
| alert_threshold | INTEGER | Alert at N% of budget | DEFAULT 80 |
| created_at | TIMESTAMP | Record creation time | NOT NULL |
| updated_at | TIMESTAMP | Last update time | NOT NULL |

### 3.5 CostRecord
Represents aggregated cost data for reporting.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | UUID | Primary key | NOT NULL, UNIQUE |
| resource_id | UUID | Foreign key to Resource | NOT NULL |
| sku_name | VARCHAR(255) | SKU display name | NOT NULL |
| sku_part_number | VARCHAR(100) | SKU identifier | NOT NULL |
| unit_price | DECIMAL(15,6) | Price per unit | NOT NULL |
| quantity | DECIMAL(15,6) | Usage quantity | NOT NULL |
| cost | DECIMAL(15,2) | Total cost | NOT NULL |
| period_start | DATE | Period start date | NOT NULL |
| period_end | DATE | Period end date | NOT NULL |
| created_at | TIMESTAMP | Record creation time | NOT NULL |

### 3.6 UsageData
Represents daily usage data from OCI.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | UUID | Primary key | NOT NULL, UNIQUE |
| resource_id | UUID | Foreign key to Resource | NOT NULL |
| date | DATE | Usage date | NOT NULL |
| quantity | DECIMAL(15,6) | Usage quantity | NOT NULL |
| unit | VARCHAR(50) | Unit of measure | NOT NULL |
| cost | DECIMAL(15,2) | Daily cost | NOT NULL |
| currency | VARCHAR(10) | Currency code | DEFAULT 'USD' |
| created_at | TIMESTAMP | Record creation time | NOT NULL |

### 3.7 PriceList
Represents OCI pricing data.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | UUID | Primary key | NOT NULL, UNIQUE |
| sku_part_number | VARCHAR(100) | SKU identifier | NOT NULL, UNIQUE |
| service_name | VARCHAR(255) | OCI service name | NOT NULL |
| product_name | VARCHAR(255) | Product description | NOT NULL |
| unit_price | DECIMAL(15,6) | Price per unit | NOT NULL |
| currency | VARCHAR(10) | Currency code | DEFAULT 'USD' |
| unit | VARCHAR(50) | Unit of measure | NOT NULL |
| region | VARCHAR(50) | Region identifier | NOT NULL |
| last_updated | TIMESTAMP | Last price update | NOT NULL |
| created_at | TIMESTAMP | Record creation time | NOT NULL |

### 3.8 PriceHistory
Tracks historical price changes.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | UUID | Primary key | NOT NULL, UNIQUE |
| price_id | UUID | Foreign key to PriceList | NOT NULL |
| unit_price | DECIMAL(15,6) | Historical price | NOT NULL |
| effective_date | DATE | When price was effective | NOT NULL |
| created_at | TIMESTAMP | Record creation time | NOT NULL |

## 4. Indexes

```sql
-- Compartment indexes
CREATE INDEX idx_compartment_tenancy ON compartments(tenancy_id);
CREATE INDEX idx_compartment_parent ON compartments(parent_id);

-- Resource indexes
CREATE INDEX idx_resource_compartment ON resources(compartment_id);
CREATE INDEX idx_resource_type ON resources(resource_type);
CREATE INDEX idx_resource_ocid ON resources(ocid);

-- Cost record indexes
CREATE INDEX idx_cost_resource ON cost_records(resource_id);
CREATE INDEX idx_cost_period ON cost_records(period_start, period_end);
CREATE INDEX idx_cost_sku ON cost_records(sku_part_number);

-- Usage data indexes
CREATE INDEX idx_usage_resource ON usage_data(resource_id);
CREATE INDEX idx_usage_date ON usage_data(date);

-- Price list indexes
CREATE INDEX idx_price_sku ON price_list(sku_part_number);
CREATE INDEX idx_price_service ON price_list(service_name);
```

## 5. Enumerations

### 5.1 ResourceType
```python
class ResourceType(Enum):
    ORACLE_DB = "oracle_db"
    MYSQL = "mysql"
    SQL_SERVER = "sql_server"
    AUTONOMOUS_DB = "autonomous_db"
```

### 5.2 PeriodType
```python
class PeriodType(Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"
```

### 5.3 BudgetStatus
```python
class BudgetStatus(Enum):
    HEALTHY = "healthy"      # < 80% consumed
    WARNING = "warning"      # 80-100% consumed
    EXCEEDED = "exceeded"    # > 100% consumed
```

## 6. Data Flow

### 6.1 Resource Discovery Flow
```
OCI API → Resource Discovery Service → Database
   │
   ├── Identity API → Compartments
   ├── Database API → Oracle DB, MySQL
   ├── Compute API → Instances (SQL Server)
   └── Autonomous DB API → Autonomous Databases
```

### 6.2 Cost Calculation Flow
```
OCI Usage API → Cost Calculator Service → Database
   │
   ├── Fetch usage data by resource
   ├── Apply current prices from PriceList
   ├── Calculate costs per resource
   └── Store in CostRecord & UsageData
```

### 6.3 Price Update Flow
```
OCI Price List API → Price Updater Service → Database
   │
   ├── Fetch latest prices
   ├── Compare with existing prices
   ├── Update PriceList if changed
   └── Log to PriceHistory
```

## 7. Caching Strategy

| Data Type | Cache Duration | Invalidation |
|-----------|---------------|--------------|
| Compartments | 1 hour | Manual refresh |
| Resources | 15 minutes | Manual refresh |
| Usage Data | 1 hour | Auto-refresh |
| Price List | 24 hours | Manual refresh |
| Cost Records | Real-time calc | On demand |
