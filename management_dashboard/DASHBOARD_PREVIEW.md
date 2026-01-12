# Management Dashboard - Visual Preview

## Overview
The Management Dashboard is a comprehensive annual KPI dashboard for ERPNext that provides executives with key financial and operational metrics.

## Layout Structure

### 1. **Filter Panel** (Top Section)
```
┌─────────────────────────────────────────────────────────────────┐
│  FILTERS                                                         │
├─────────────────────────────────────────────────────────────────┤
│  [Year: 2024]  [Company: ABC Corp]  [Cost Center: ...]          │
│  [Branch: ...]  [Project: ...]  [Customer Group: ...]           │
│  [Supplier Group: ...]  [Item Group: ...]                        │
│                                                                   │
│  Period: [Monthly ▼]  [Refresh] [Export CSV] [Excel] [PDF] [Print]│
└─────────────────────────────────────────────────────────────────┘
```

**Features:**
- Year selector (defaults to current year)
- Company dropdown
- Multi-select filters for Cost Center, Branch, Project, Customer/Supplier/Item Groups
- Period type toggle (Monthly/Quarterly/Weekly)
- Export and print buttons
- Filters are saved to localStorage

### 2. **KPI Cards Grid** (Main Section)
```
┌─────────────────────────────────────────────────────────────────┐
│  Annual Summary — 2024 vs 2023                                  │
│  Current Period: 2024-01-01 → 2024-12-31                        │
├──────────────┬──────────────┬──────────────┬──────────────┐
│ Sales Invoice│ Sales Invoice│ Sales Order  │ Delivery Note│
│ (Net)        │ (Gross)      │              │              │
│ $1,250,000   │ $1,350,000   │ $1,400,000   │ $1,200,000   │
│ Previous:    │ Previous:    │ Previous:    │ Previous:    │
│ $1,100,000   │ $1,200,000   │ $1,300,000   │ $1,100,000   │
│ +13.6%        │ +12.5%       │ +7.7%        │ +9.1%        │
├──────────────┼──────────────┼──────────────┼──────────────┤
│ Net Profit   │ AR Outstanding│ AP Outstanding│ Cash & Bank │
│ $150,000     │ $250,000     │ $180,000     │ $500,000     │
│ Previous:    │              │              │              │
│ $120,000     │              │              │              │
│ +25.0%       │              │              │              │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

**KPI Cards Features:**
- Clickable cards (drill down to detailed views)
- Current vs Previous year comparison
- Percentage change indicators (green for positive, red for negative)
- Negative values highlighted in red
- Hover effects for better UX

### 3. **Charts Section**
```
┌─────────────────────────────────────┬─────────────────────────────┐
│  Sales vs Purchases (Monthly)       │  AR Aging                   │
│                                      │                              │
│  [Bar Chart]                         │  [Bar Chart]                 │
│  Sales: Blue bars                   │  0-30, 31-60, 61-90, 90+     │
│  Purchases: Orange bars             │                              │
│                                      │                              │
└─────────────────────────────────────┴─────────────────────────────┘
┌─────────────────────────────────────┐
│  AP Aging                           │
│                                      │
│  [Bar Chart]                         │
│  0-30, 31-60, 61-90, 90+            │
│                                      │
└─────────────────────────────────────┘
```

**Chart Features:**
- Interactive bar charts using Frappe Charts
- Sales vs Purchases comparison over time
- AR/AP aging buckets visualization
- Responsive grid layout

### 4. **Breakdowns & Details Section**
```
┌─────────────────────────────────────┬─────────────────────────────┐
│  Cash & Bank Balances               │  Top Overdue Customers      │
│                                      │                              │
│  • Main Bank Account (Bank)         │  • Customer A → $50,000     │
│    $300,000                         │  • Customer B → $35,000     │
│  • Petty Cash (Cash)                │  • Customer C → $25,000     │
│    $5,000                           │                              │
│  • Savings Account (Bank)           │                              │
│    $195,000                         │                              │
└─────────────────────────────────────┴─────────────────────────────┘
┌─────────────────────────────────────┬─────────────────────────────┐
│  Top Suppliers                      │  Customer Health            │
│                                      │                              │
│  • Supplier X → $200,000           │  New Customers: 15          │
│  • Supplier Y → $150,000            │                              │
│  • Supplier Z → $100,000            │                              │
└─────────────────────────────────────┴─────────────────────────────┘
┌─────────────────────────────────────┐
│  HR Metrics                         │
│                                      │
│  Headcount: 45                       │
│  Payroll Cost: $450,000              │
│  Open Positions: 3                   │
│                                      │
└─────────────────────────────────────┘
```

**Breakdown Features:**
- Clickable customer/supplier links (navigate to detail pages)
- Account type badges
- Formatted currency values
- Clean list layouts

## Design Features

### Visual Style
- **Color Scheme:**
  - Primary: Blue (#2563eb)
  - Success: Green (#10b981)
  - Warning: Orange (#f59e0b)
  - Danger: Red (#ef4444)
  - Cards: White background with subtle borders

### User Experience
- **Responsive Design:** Adapts to mobile, tablet, and desktop
- **RTL Support:** Full right-to-left language support
- **Loading States:** Visual feedback during data loading
- **Hover Effects:** Cards lift slightly on hover
- **Clickable KPIs:** Drill down to detailed ERPNext views
- **Filter Persistence:** Saves filter preferences

### Data Features
- **Year-over-Year Comparison:** Current vs previous year
- **Multi-Select Filters:** Filter by multiple cost centers, projects, etc.
- **Period Flexibility:** View data by month, quarter, or week
- **Export Options:** CSV, Excel (via CSV), PDF, Print
- **Audit Trail:** Logs dashboard views for compliance

## Access Control
- **Roles:** Management and System Manager only
- **Company Restrictions:** Management users see only their assigned companies
- **Permission Checks:** Validates user permissions before loading data

## Technical Highlights
- Built with Frappe Framework
- Uses Frappe Charts for visualizations
- RESTful API endpoint for data
- LocalStorage for filter persistence
- Print-friendly CSS
- Mobile-responsive grid layouts
