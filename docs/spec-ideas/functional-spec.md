# Functional Specification: Common Investor Web Application

## Product Overview

**Product Name**: Common Investor  
**Purpose**: A web application that provides deep financial and qualitative analysis of public companies using Phil Town's Rule #1 investing methodology.  
**Target Users**: Retail investors, financial analysts, and value investors seeking actionable insights based on Rule #1 principles.

---

## Functional Modules

### 1. Company Search

**Input**: Company name or ticker symbol  
**Function**: Retrieve financial data, display analysis dashboard  
**Data Sources**: SEC EDGAR, public financial APIs

---

### 2. Four M Analysis Engine

**Inputs**:
- User understanding (Meaning)
- Moat indicators (market share, IP, brand, cost advantage)
- Management quality (ROIC trends, governance info)
- Margin of Safety target (user-configurable)

**Outputs**:
- Four M status (Pass/Fail)
- Detailed explanation and links

---

### 3. Big Five Number Analysis

**Metrics**:
- Return on Invested Capital (ROIC)
- Sales Growth (10Y, 5Y, 1Y)
- EPS Growth (historical trend)
- Free Cash Flow trend (Owner Earnings)
- Debt/Equity ratio, Interest coverage

**Visuals**:
- Graphs over 10-year timeline
- Traffic-light indicator for consistency

---

### 4. Valuation Engine

**Valuation Methods**:
- Payback Time Calculator
- Ten Cap Valuation
- Discounted Cash Flow with user assumptions

**Inputs**:
- Owner Earnings (derived from cash flow)
- Growth estimates (auto & manual override)
- Discount rate (configurable)

**Outputs**:
- Intrinsic value range
- Sticker price
- Margin of safety price

---

### 5. Entry/Exit Timing Dashboard

**Features**:
- Technical charts (moving averages, RSI)
- Highlighted buy/sell zones
- Indicators when stock is “on sale”

---

### 6. Option Strategy Module

**Features**:
- Selling puts interface
- Selling calls simulator
- Risk-reward visualization

**Data**:
- Option chain (from financial APIs)
- Premiums, expiries, assignments

---

### 7. Company Profile View

**Includes**:
- Company description
- Industry context
- Moat narrative (text + indicators)
- Management scorecard
- Historical crisis performance

---

### 8. Scenario Testing UI

**Purpose**: Allow users to adjust:
- Growth rates
- Discount rate
- Owner earnings adjustments
- Confidence sliders

**Effect**:
- Update sticker price, payback time, MOS in real-time

---

### 9. User Interface Requirements

- Responsive web app (desktop first)
- Simple input field (ticker/company)
- Results: tabbed interface (Four Ms, Financials, Valuation, MoS, Charts)
- Download/export capability (PDF, CSV)
- Theme: professional, clean

---

## Non-Functional Requirements

- Modular architecture for cloud deployment (AWS, Azure ready)
- Data caching to optimize SEC/API requests
- Authentication (optional for premium features)
- CI/CD pipeline for easy iteration

---

## Future Enhancements

- Watchlists with alerting when price drops below MOS
- Community ratings for moat & management
- Machine learning to detect pattern consistency
- Mobile version

---