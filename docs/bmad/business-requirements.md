# OCI Cost Manager - Business Requirements

## 1. Executive Summary

The OCI Cost Manager is a web-based application designed to help organizations monitor, analyze, and optimize their Oracle Cloud Infrastructure spending. It provides real-time cost visibility, budget validation, and automated price updates from official OCI sources.

## 2. Business Objectives

### 2.1 Primary Goals
- **Cost Visibility**: Provide clear, actionable insights into OCI resource costs
- **Budget Control**: Enable proactive budget management with validation and alerts
- **Resource Optimization**: Identify cost-saving opportunities through detailed analysis
- **Price Accuracy**: Maintain up-to-date pricing from official OCI sources

### 2.2 Success Metrics
- Reduce unplanned cloud overspend by 20%
- Decrease time spent on cost reporting by 80%
- Achieve 100% budget compliance visibility
- Maintain pricing accuracy within 24 hours of OCI updates

## 3. User Stories

### 3.1 Cloud Administrator
- **US-001**: As a cloud admin, I want to view all database resources across compartments so I can understand our infrastructure landscape
- **US-002**: As a cloud admin, I want to filter resources by compartment and type so I can focus on specific areas
- **US-003**: As a cloud admin, I want to see cost breakdowns by resource name so I can identify expensive resources

### 3.2 Finance Manager
- **US-004**: As a finance manager, I want to set monthly/yearly budgets so I can control spending
- **US-005**: As a finance manager, I want to compare actual vs budgeted costs so I can track variance
- **US-006**: As a finance manager, I want to export reports to Excel/PDF so I can share with stakeholders
- **US-007**: As a finance manager, I want to see cost forecasts so I can plan future budgets

### 3.3 IT Manager
- **US-008**: As an IT manager, I want to see cost trends over time so I can identify patterns
- **US-009**: As an IT manager, I want alerts when costs exceed thresholds so I can take action
- **US-010**: As an IT manager, I want to see the top expensive resources so I can prioritize optimization

## 4. Functional Requirements

### 4.1 Authentication & Authorization
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-001 | Support OCI API key authentication | High |
| FR-002 | Support multiple tenancy configurations | Medium |
| FR-003 | Role-based access control (Admin, Viewer) | Medium |
| FR-004 | Secure credential storage | High |

### 4.2 Resource Discovery
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-010 | List all compartments in hierarchical view | High |
| FR-011 | Discover Oracle Database systems | High |
| FR-012 | Discover MySQL Database systems | High |
| FR-013 | Discover compute instances (for SQL Server) | High |
| FR-014 | Discover Autonomous Databases | Medium |
| FR-015 | Filter resources by compartment | High |
| FR-016 | Filter resources by type | High |
| FR-017 | Search resources by name | Medium |

### 4.3 Cost Reporting
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-020 | Show costs by resource name | High |
| FR-021 | Show costs by SKU/service type | High |
| FR-022 | Show costs by compartment | High |
| FR-023 | Toggle monthly/yearly view | High |
| FR-024 | Show cost breakdown (compute, storage, license) | High |
| FR-025 | Historical cost data (last 12 months) | Medium |
| FR-026 | Cost trend visualization | Medium |

### 4.4 Budget Management
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-030 | Create budgets (monthly/yearly) | High |
| FR-031 | Assign budgets to compartments | Medium |
| FR-032 | Compare actual vs budget | High |
| FR-033 | Show variance (amount and percentage) | High |
| FR-034 | Budget health indicators (green/yellow/red) | High |
| FR-035 | Budget forecast based on burn rate | Medium |
| FR-036 | Budget alerts when threshold exceeded | Medium |

### 4.5 Price Management
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-040 | Fetch prices from OCI Price List API | High |
| FR-041 | Cache prices locally | High |
| FR-042 | Manual price refresh option | High |
| FR-043 | Show price per unit for each SKU | Medium |
| FR-044 | Alert when prices change | Low |
| FR-045 | Price history tracking | Low |

### 4.6 Export & Reporting
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-050 | Export to CSV | High |
| FR-051 | Export to Excel | High |
| FR-052 | Export to PDF | Medium |
| FR-053 | Scheduled report generation | Low |
| FR-054 | Email report delivery | Low |

## 5. Non-Functional Requirements

### 5.1 Performance
- Dashboard load time < 3 seconds
- Resource discovery < 10 seconds for 100 resources
- Cost calculation < 5 seconds

### 5.2 Security
- All API credentials encrypted at rest
- HTTPS for all communications
- No credentials in logs or error messages
- Session timeout after 30 minutes of inactivity

### 5.3 Availability
- 99% uptime during business hours
- Graceful degradation if OCI API unavailable

### 5.4 Usability
- Responsive design (desktop, tablet)
- Intuitive navigation
- Contextual help tooltips
- Clear error messages

## 6. Out of Scope (Phase 1)
- Multi-cloud support (AWS, Azure)
- Cost optimization recommendations (AI-based)
- Chargeback/showback functionality
- Custom tagging management
- Resource provisioning

## 7. Assumptions
- Users have valid OCI API credentials
- OCI Usage API access is enabled for the tenancy
- Users have appropriate IAM permissions to read resources and usage data

## 8. Constraints
- OCI Usage API rate limits
- OCI Price List API update frequency
- Browser compatibility (Chrome, Firefox, Edge - latest 2 versions)

## 9. Glossary
| Term | Definition |
|------|------------|
| Compartment | OCI logical container for organizing resources |
| SKU | Stock Keeping Unit - unique identifier for a billable service |
| OCPU | Oracle Compute Unit - measure of compute capacity |
| Tenancy | Top-level OCI account container |
| Usage API | OCI API for retrieving cost and usage data |
