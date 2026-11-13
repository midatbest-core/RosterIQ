# RosterIQ — Smart Roster Management System

> **Submission for DataStraw Tech Internship Assessment**  
> **Candidate**: Antigravity AI Engineering Candidate  
> **Submission Recipients**: `ozair.shaikh@datastraw.in`, `aryan.jaiswal@datastraw.in`  
> **CC**: `talent@datastraw.in`  
> **Subject**: `Smart Roster Management System Assignment - Antigravity`

---

## 1. Executive Summary

**RosterIQ** is a deterministic, explainable, and resilient workforce scheduling platform built for multi-brand, multi-pod operational environments managing 30+ employees across specialized operational processes (e.g., Customer Support, Account Management, Retention, NDR).

The platform features an **Enterprise SaaS UI/UX redesign** synthesizing the world's leading workforce management products:
- **Assembled**: Clean, modern visual appearance, minimal visual clutter, high information density without overwhelm, and fluid contextual detail drawers.
- **Calabrio ONE**: Dedicated workforce scheduling workspace, detailed shift & interval visualization, employee inspection, and granular operational controls.
- **NICE CXone WFM**: Operational visibility, dedicated exception & conflict management, structured drill-downs, and strict manager authorization workflows for cross-pod reassignments.

Under the hood, RosterIQ implements **transparent interval algebra** and an **independent zero-trust validation engine**:
1. **Deterministic 3-Stage Scheduling**: Resolves calendar demand $\to$ prioritizes primary resource allocations $\to$ seeks same-pod backups $\to$ surfaces cross-pod candidates for explicit Operations Manager approval.
2. **Strict Interval Constraints**: Guarantees exactly one same-day working shift per employee per date, enclosing strictly non-overlapping process allocations with complete interval coverage.
3. **Approved Holiday Precedence**: Evaluates `Date Override → Recurring Weekday Rule → Holiday Behaviour (CLOSED, NORMAL, REDUCED)`. Public holidays affect brand-process demand, not employee availability.
4. **Governed Cross-Pod Reassignment**: Reassignment across pod boundaries requires authenticated Operations Manager authorization (`confirm_cross_pod_approval=True`), recording an immutable audit trail (`approved_by_user_id` and `approved_at`).
5. **Unified 5-View Schedule Explorer**: Instant switching between **Company**, **Pod**, **Brand**, **Process**, and **Employee** perspectives backed by a single high-performance grid API.
6. **Immutable Versioning**: Published rosters are locked and immutable. Changes spawn child draft versions (`v2`, `v3`) with full historical diff traceability. Configuration drifts mark affected drafts as `STALE`.

---

## 2. Quickstart & Local Installation Guide

### Prerequisites
- Python 3.11+ (Python 3.12 / 3.14 verified)
- Node.js 18+ & npm
- Git

### A. Backend Setup

```bash
# 1. Navigate to backend directory
cd backend

# 2. Create and activate a virtual environment
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On macOS/Linux:
# source .venv/bin/activate

# 3. Install backend dependencies
pip install -e .

# 4. Set environment variable (SQLite demo database or PostgreSQL)
# For local SQLite:
$env:ROSTERIQ_DATABASE_URL="sqlite+pysqlite:///rosteriq_demo.db"
# For PostgreSQL:
# $env:ROSTERIQ_DATABASE_URL="postgresql+psycopg://rosteriq:rosteriq@localhost:5432/rosteriq"

# 5. Run Alembic Database Migrations
python -m alembic upgrade head

# 6. Seed Realistic Deterministic Demo Data (32 employees, 4 pods, 15 brands, leaves, holidays)
python -m app.scripts.seed_demo_data

# 7. Start the FastAPI Application
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation will be live at: `http://localhost:8000/docs`

### B. Frontend Setup

```bash
# 1. Open a new terminal and navigate to frontend directory
cd frontend

# 2. Install frontend dependencies
npm install

# 3. Start Vite development server
npm run dev
```
The Frontend UI will be live at: `http://localhost:5173`

### Development Credentials
- **Admin**: `admin@example.com` / `AdminPass123!` (Role: Admin)
- **Operations Manager**: `ops@example.com` / `OpsManager123!` (Role: Operations Manager)

---

## 3. 3-Minute Demo Walkthrough (Assessment Scenario 4.F)

1. **Sign In**: Navigate to `http://localhost:5173` and log in with `admin@example.com` / `AdminPass123!`.
2. **Master Data Verification**:
   - Open **Employees**: View 32 employees organized across 4 pods (Alpha, Beta, Gamma, Delta) with leads, skills, and capacities.
   - Open **Brands**: View 15 brands (12 single-resource ~80%, 3 multi-resource) and their active processes.
3. **Generate Roster**:
   - Navigate to **Roster Management**.
   - Click **Generate Roster**, choose November 2026, and submit.
   - The deterministic engine generates shifts, allocations, and computes calendar demand across all 30 days.
4. **Inspect the 5 Viewing Modes**:
   - Use the view tabs in the header: **Company**, **Pod**, **Brand**, **Process**, and **Employee**.
   - Notice how all 5 views cleanly pivot the same unified schedule.
5. **Detect Conflict (Assessment Scenario 4.F - Kavya Organics)**:
   - Notice the Red Conflict alert banner: `Kavya Organics — Customer Support` on November 4, 2026 has an `UNCOVERED_SLOT` conflict.
   - **Reason**: Diya Patel is the sole primary resource for Kavya Organics CS and has approved medical leave from Nov 02–06.
6. **Smart Backup Discovery & Reassignment**:
   - Click **Reassign** on the conflict card or cell.
   - The backup discovery algorithm evaluates all 32 employees, filtering out employees on leave or with overlapping shifts, and ranks eligible cross-pod and same-pod candidates by skill proficiency and current workload.
   - Select the recommended candidate. If cross-pod, the system triggers the **Operations Manager Authorization** modal requiring confirmation.
   - Confirm and apply: the slot is filled, the conflict is immediately resolved, and the schedule updates in real-time.
7. **Publish & Versioning**:
   - Click **Publish Roster**: the roster transitions to `PUBLISHED` and becomes strictly read-only.
   - To make further adjustments, click **Create Revision**: a child draft version (e.g. `v2`) is spawned, preserving historical auditability.

---

## 4. Test Suite & Verification Results

### Unit & Integration Tests (Pytest)
Run from `backend/`:
```bash
python -m pytest tests
```
**Result**: `29 passed in 4.04s`
- `tests/test_auth.py`: JWT token issue, cookie session handling, role enforcement (`ADMIN`, `OPERATIONS_MANAGER`, `EMPLOYEE`).
- `tests/test_crud_flow.py`: Pods, Employees, Skills, Brands, Processes CRUD lifecycles.
- `tests/test_migrations.py`: Schema validation, upgrade and downgrade integrity.
- `tests/test_reconciled_models.py`: Model constraints, check constraints, cascade behaviors, and interval invariants.
- `tests/test_roster_engine.py`: Demand resolution, recurring operating patterns, holiday precedence (Override → Weekday → Holiday), capacity limits, cross-pod restriction, non-overlapping multi-brand allocations, soft preference scoring.
- `tests/test_roster_api.py`: Roster generation, 5-view grid querying, versioning lifecycle.
- `tests/test_reassignment_and_stale.py`: Reassignment preview and apply, cross-pod manager authorization requirement (HTTP 403 vs 201), approval auditing (`approved_by_user_id`), stale draft marking upon config drift, published roster immutability.

### Runtime End-to-End Verification
Run from `backend/`:
```bash
python -m app.scripts.runtime_e2e_verification
```
**Result**: `ALL 9 END-TO-END WORKFLOWS VERIFIED SUCCESSFULLY!`
1. Admin authentication & CSRF cookie verification.
2. Master data loading (32 employees, 4 pods, 15 brands, 27 brand-processes).
3. Deterministic roster generation.
4. All 5 viewing modes rendered.
5. Expected conflict detection (Diya Patel medical leave on Kavya Organics).
6. Backup candidate discovery & ranking.
7. Authorized reassignment application.
8. Database persistence & conflict resolution verification.
9. Child roster version spawning (`v1` $\to$ `v2`).

### Frontend Production Build
Run from `frontend/`:
```bash
npm run build
```
**Result**: Clean TypeScript & Vite compilation in 768ms with zero errors.

---

## 5. Architectural Thinking Questions (Assessment Section 8)

### Q1: How would you handle an employee who works across 3 brands with different operating hours?
**RosterIQ Solution**:
- **Single Enclosing Shift**: Under RosterIQ's interval model, an employee is assigned at most one continuous working shift per date (e.g., `09:00 - 18:00`, 9 hours total including standard break).
- **Non-Overlapping Process Allocations**: The engine divides that shift into discrete, non-overlapping interval slices matching each brand's operating requirements (e.g., Brand A: `09:00 - 12:00`, Brand B: `12:30 - 15:30`, Brand C: `15:30 - 18:00`).
- **Interval Validation**: The `IndependentValidator` asserts that $\sum \text{duration}(\text{allocations}) \le \text{shift\_duration}$ and that no two allocation intervals intersect $[\text{start}_i, \text{end}_i) \cap [\text{start}_j, \text{end}_j) = \emptyset$. If the brands' operating windows cannot be reconciled within a single same-day shift window without split shifts, the scheduler flags an `UNRESOLVED_SCHEDULE_SPLIT` conflict rather than creating disjoint shifts.

### Q2: If a brand changes operating hours mid-month, what happens to the existing roster?
**RosterIQ Solution**:
- **Cryptographic Config Hashing**: The system continuously computes a deterministic SHA-256 hash across all active operating patterns, overrides, and brand-process configurations.
- **Automatic Stale Draft Invalidation**: When an operating pattern is updated, any unapproved draft roster matching that period is immediately marked `STALE`. Stale drafts are blocked from being published until regenerated or refreshed.
- **Published Roster Immutability**: If the active roster for that month is already `PUBLISHED`, it is immutable and legally locked. To absorb the mid-month change, an Operations Manager clicks **Create Child Version**, which branches a child draft (`v2`) from the published parent. The engine then resolves demand against the new operating hours, highlights the differential delta, surfaces any newly uncovered slots, and allows controlled reassignment before publishing `v2`.

### Q3: How would you scale this system from 30 to 300 employees? What would break first?
**RosterIQ Solution & Scaling Analysis**:
1. **What breaks first?**: The naive combinatorial backup search and synchronous single-request roster generation. Generating 300 employees across 150 brand-processes for 31 days represents $\approx 9,300$ employee-days and tens of thousands of allocation checks. In a single HTTP request, this would risk HTTP timeout (30s+ gateway timeout).
2. **Mitigation Strategy**:
   - **Pod-Level Horizontal Partitioning**: Because pods are largely autonomous organizational units, demand resolution and primary assignment can be partitioned and computed in parallel across worker tasks (using Celery / Redis or Python `ProcessPoolExecutor`).
   - **Asynchronous Job Execution**: Decouple roster generation into a background task: `POST /rosters/generate` returns `202 Accepted` with a `job_id`, polling via SSE/WebSockets for progress.
   - **Database Indexing & Batch Fetching**: The database schema is already equipped with composite indexes on `(roster_id, employee_id, date)` and `(brand_process_id, date)`. At 300 employees, PostgreSQL bulk-insert operations (`insert().values([...])`) are utilized instead of individual ORM model instances.

### Q4: How does the system ensure fairness in weekend shift distribution among pod members?
**RosterIQ Solution**:
- **Workload & Weekend Shift Accumulator**: During candidate ranking and scheduling, RosterIQ tracks cumulative weekend shifts ($S_{\text{weekend}}$) assigned to each employee over a rolling 8-week lookback window.
- **Soft Constraint Scoring**: When multiple same-pod backup employees have the requisite skill for a weekend slot, the candidate scoring function penalizes employees who have already worked weekend shifts:
  $$\text{Score}(e) = \alpha \cdot \text{SkillProficiency}(e) - \beta \cdot S_{\text{weekend}}(e) - \gamma \cdot \text{PreferencePenalty}(e)$$
- **Rotating Weekend-Off Guarantee**: Employees with weekly-off preferences for Saturday/Sunday are respected unless demand mandates coverage; if assigned, the fairness counter increments, giving them priority for consecutive weekends off in the subsequent cycle.

### Q5: If an entire pod is unavailable (e.g., team offsite), how does the system handle coverage?
**RosterIQ Solution**:
1. **Bulk Leave Logging**: An offsite is recorded as an approved `EmployeeUnavailability` entry across all members of that pod for the specified dates.
2. **Automatic Conflict Flagging**: The scheduler detects that all primary and same-pod backup resources are unavailable, flagging `UNCOVERED_SLOT` conflicts for all brand-processes owned by that pod.
3. **Cross-Pod Candidate Discovery**: The backup ranking engine queries active, qualified employees from other pods (e.g. Beta, Gamma) who possess the necessary process skills and have available shift capacity.
4. **Operations Manager Bulk Authorization**: In accordance with RosterIQ's governance policy, cross-pod allocations are not silently or automatically forced. Instead, the UI presents a **Bulk Offsite Reassignment** batch workflow where the Operations Manager reviews the proposed cross-pod coverage matrix and provides single-action authenticated approval (`confirm_cross_pod_approval=True`).

### Q6: What metrics would you track to measure roster quality over time?
**RosterIQ Solution**:
- **Coverage Fill Rate**: $\frac{\text{Actual Allocated Hours}}{\text{Required Demand Hours}} \times 100\%$ (target: 100%).
- **Sole-Resource Vulnerability Index (SRVI)**: Percentage of brand-processes where only 1 employee possesses the required skill and primary assignment (identifies critical operational single points of failure).
- **Cross-Pod Dependency Ratio**: $\frac{\text{Cross-Pod Reassignments}}{\text{Total Allocations}} \times 100\%$ (target: $< 5\%$; high ratio indicates flawed pod staffing).
- **Preference Satisfaction Score**: Percentage of soft weekly-off preferences fulfilled without creating hard conflicts.
- **Churn / Revision Rate**: Number of child versions (`v2`, `v3`) created post-publish, measuring schedule volatility and mid-month disruption.

### Q7: How would you handle split shifts (e.g., 4 hours morning + 4 hours evening)?
**RosterIQ Solution**:
- **Current MVP Architectural Rule**: In accordance with the approved architecture specification, split shifts are strictly prohibited in the core MVP to guarantee employee wellbeing and simplify interval algebra.
- **Production Extension (Day Split Model)**:
  - If a business process explicitly requires split shifts, `employee_shifts` would support a discrete `shift_sequence` (e.g., Shift 1: `08:00 - 12:00`, Shift 2: `16:00 - 20:00`).
  - **Mandatory Rest Interval Check**: The validator must enforce a statutory minimum break duration between split shifts (e.g., $\ge 4$ continuous hours of rest) and verify that total spread-over ($\text{end}_2 - \text{start}_1$) does not exceed 12 hours.
  - Split shifts would be designated as a distinct `ShiftType.SPLIT` requiring explicit employee opt-in via preferences.

### Q8: How does the system handle timezone differences if employees and brands are in different regions?
**RosterIQ Solution**:
- **UTC Canonical Storage**: All shift and allocation intervals are stored internally with explicit timezone awareness (`DateTime(timezone=True)`) or paired with an IANA timezone identifier (e.g., `Asia/Kolkata`, `America/New_York`, `Europe/London`).
- **Brand Operating Window Localization**: A brand's operating pattern is defined in its local operating timezone (e.g., US Support: `09:00 - 17:00 EST`).
- **Interval Projection to Employee Local Time**: When generating schedules, the engine projects the brand's required UTC interval $[\text{start}_{\text{UTC}}, \text{end}_{\text{UTC}})$ into the employee's local timezone to verify that it fits within their standard working hours and local labor laws (e.g., preventing unscheduled nocturnal shifts unless designated for night-shift teams).
- **Localized UI Grid Rendering**: The frontend grid allows users to toggle display between "Brand Local Time", "Employee Local Time", or "Company Standard UTC".

---

## 6. Project Structure

```
Roster/
├── README.md                      # Comprehensive project documentation & answers
├── compose.yaml                   # PostgreSQL local development container
├── .env.example                   # Environment variable template
├── backend/
│   ├── alembic/                   # Database migrations (Phase 1 & Phase 2)
│   ├── app/
│   │   ├── core/                  # Security, config, error handlers
│   │   ├── db/                    # SQLAlchemy database engine and session
│   │   ├── modules/
│   │   │   ├── auth/              # JWT auth, user models, role dependencies
│   │   │   ├── workforce/         # Pods, Employees, Skills, Availability
│   │   │   ├── operations/        # Brands, Processes, Operating Patterns, Holidays
│   │   │   └── roster/            # Rosters, Shifts, Allocations, Conflicts
│   │   │       ├── engine/        # DeterministicScheduler, DemandResolver, Validator
│   │   │       ├── router.py      # Unified 5-view grid, Reassignment, Versioning
│   │   │       └── schemas.py     # Pydantic request/response schemas
│   │   └── scripts/
│   │       ├── seed_demo_data.py  # Deterministic seed data (32 emps, 15 brands)
│   │       └── runtime_e2e_verification.py # Full 9-step runtime test
│   ├── tests/                     # 29 Pytest integration & unit tests
│   └── pyproject.toml             # Backend dependencies & metadata
└── frontend/
    ├── src/
    │   ├── api/                   # Centralized API service layer
    │   ├── components/
    │   │   ├── layout/            # AppShell, Sidebar, Topbar, DetailDrawer
    │   │   ├── common/            # StatusBadge, MetricCard, Modal
    │   │   └── roster/            # CalendarToolbar, AllocationCard, AllocationDetailDrawer,
    │   │                          # GenerateRosterModal, ReassignmentModal
    │   ├── screens/
    │   │   ├── DashboardScreen.tsx      # Operational KPI overview, coverage %, real API metrics
    │   │   ├── RosterCalendarScreen.tsx # Core scheduling workspace (5 views, sticky headers)
    │   │   ├── ConflictsScreen.tsx      # Dedicated exception management workspace
    │   │   ├── WorkforceScreen.tsx      # Directory, Pods, Availability & Leaves
    │   │   ├── OperationsScreen.tsx     # Brands, Processes, Brand-Process links, Assignments
    │   │   ├── AuditHistoryScreen.tsx   # Roster versioning tree, immutable audit log
    │   │   └── LoginScreen.tsx          # Branded enterprise login with quick-fill
    │   ├── App.tsx                # Main view router & shell coordinator
    │   └── main.tsx
    ├── package.json
    └── vite.config.ts             # Vite configuration with TailwindCSS
```

---

## 7. Submission Checklist & Assessment Verification

- [x] **Organisational Structure**: Company $\to$ Pods $\to$ Employees and Company $\to$ Brands $\to$ Processes $\to$ Primary Assignments fully modeled and dynamically manageable.
- [x] **Deterministic Scheduling Engine**: Transparent interval algebra matching demand, capacity, and skills.
- [x] **Independent Validation Engine**: Zero-trust validator detecting hard conflicts and soft warnings.
- [x] **Approved Holiday Precedence**: Override $\to$ Weekday Rule $\to$ Holiday Behaviour implemented.
- [x] **Cross-Pod Governance**: Reassignment strictly gated behind authenticated Operations Manager approval with audit logging.
- [x] **5 Required Views**: Company, Pod, Brand, Process, and Employee views functional on the frontend and backend.
- [x] **30+ Realistic Dataset**: 32 employees, 4 pods, 15 brands (80% single-resource), leaves, and holiday scenarios seeded.
- [x] **Immutable Versioning**: Child version branching (`v1` $\to$ `v2`) and stale draft detection verified.
- [x] **29/29 Pytest Tests Passing**.
- [x] **9/9 Runtime Verification Workflows Passing**.
- [x] **Frontend Builds Cleanly in Production Mode**.

---

## 8. Export Capabilities: CSV and Google Sheets Integration

RosterIQ provides dual export channels for operational rosters: **Direct Downloadable CSV** and **Direct-to-Google Sheets Export**, maintaining 100% data parity and strict role-based access control across all 5 operational views.

### A. Direct Downloadable CSV
- **Immediate Download**: Generates RFC 4180-compliant CSV files with UTF-8 BOM (`utf-8-sig`) for native Microsoft Excel and Google Sheets character fidelity.
- **Unified 14-Column Format**:
  `Date, Day of Week, Pod, Employee Code, Employee Name, Brand, Process, Shift Start, Shift End, Allocation Start, Allocation End, Allocation Status, Cross-Pod Approved, Reassigned From`
- **Supported Views**:
  - `company`: Complete workforce shift & allocation matrix.
  - `pod`: Filtered by specific pod (or locked to Pod Lead's assigned pod).
  - `brand`: Filtered by brand portfolio (or locked to Brand User's assigned brand).
  - `process`: Filtered by operational process (Customer Support, Retention, NDR).
  - `employee`: Personal shift and task checklist for individual personnel.
- **Strict Tenant & Role Scoping**:
  - `ADMIN` & `OPERATIONS_MANAGER`: Full export across all views and entities.
  - `POD_LEAD`: Restricted strictly to authorized pod; foreign pod or cross-entity exports return `403 Forbidden`.
  - `BRAND_USER`: Restricted strictly to assigned brand; foreign brand exports return `403 Forbidden`.
  - `EMPLOYEE`: Restricted strictly to personal schedule; foreign record exports return `403 Forbidden`.
- **Zero Credentials/PII**: Password hashes, tokens, secret keys, and personal contact details are strictly excluded.

### B. Direct Google Sheets Export
- **Cloud-Native Automation**: Automatically creates a new Google Spreadsheet via the official Google Sheets API v4 (`spreadsheets.create`).
- **Professional Formatting**: Applies styled header rows (dark slate background `#1E293B`, bold white text `#FFFFFF`, center-aligned), freezes the header row, auto-resizes column dimensions, and populates data via `spreadsheets.values.update`.
- **Returned Deliverable**: Returns `spreadsheet_id` and the direct browser URL (`https://docs.google.com/spreadsheets/d/{id}/edit`), automatically opening the new sheet in a new tab.
- **Decoupled & Resilient**: Google Sheets integration is completely decoupled from core scheduling. If Google credentials are not configured on the server, the application degrades gracefully: the UI informs the user, and direct CSV download remains immediately accessible.

### C. Google Cloud Project & OAuth 2.0 Setup Guide

To enable live Google Sheets exports in your deployment:

#### 1. Create Google Cloud Project
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Click **Select a project** $\to$ **New Project**.
3. Name the project (e.g., `RosterIQ-Workforce`) and click **Create**.

#### 2. Enable Required APIs
1. In the Google Cloud Console, navigate to **APIs & Services** $\to$ **Library**.
2. Search for and enable:
   - **Google Sheets API**
   - **Google Drive API** (used for file creation and permissions)

#### 3. Configure OAuth Consent Screen
1. Navigate to **APIs & Services** $\to$ **OAuth consent screen**.
2. Choose **Internal** (if Google Workspace organization) or **External** (for development/testing).
3. Fill in the App Name (`RosterIQ`), User support email, and Developer contact information.
4. Under **Scopes**, click **Add or Remove Scopes** and select:
   - `https://www.googleapis.com/auth/spreadsheets`
   - `https://www.googleapis.com/auth/drive.file`
5. If **External**, add your test Google account emails under **Test users**. Save and continue.

#### 4. Create OAuth 2.0 Client Credentials
1. Navigate to **APIs & Services** $\to$ **Credentials** $\to$ **Create Credentials** $\to$ **OAuth client ID**.
2. Select Application type: **Web application**.
3. Add **Authorized redirect URIs**:
   - `http://localhost:5173/oauth/google/callback` (local frontend dev)
   - `http://localhost:8000/api/v1/auth/google/callback` (backend API callback)
4. Click **Create** and securely copy the **Client ID** and **Client Secret**.

#### 5. Alternative: Server-to-Server Service Account Setup
For automated headless enterprise exports without interactive user login:
1. In **Credentials**, click **Create Credentials** $\to$ **Service account**.
2. Name the service account (e.g., `rosteriq-sheet-exporter`) and click **Done**.
3. Click the created service account $\to$ **Keys** tab $\to$ **Add Key** $\to$ **Create new key** $\to$ **JSON**.
4. Download the generated JSON key file to a secure directory (never commit this file).

#### 6. Configure Environment Variables
Set the following environment variables in `backend/.env` or your hosting runtime:

```bash
# Option A: User OAuth 2.0 Flow
ROSTERIQ_GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
ROSTERIQ_GOOGLE_CLIENT_SECRET="your-client-secret"
ROSTERIQ_GOOGLE_REDIRECT_URI="http://localhost:5173/oauth/google/callback"

# Option B: Server Service Account (JSON file path or string)
ROSTERIQ_GOOGLE_SERVICE_ACCOUNT_FILE="/path/to/service-account.json"
# Or inline JSON string:
# ROSTERIQ_GOOGLE_SERVICE_ACCOUNT_INFO='{"type": "service_account", ...}'
```

*Note: If no Google credentials are set, `GET /api/v1/rosters/export/google-sheets/status` cleanly reports `enabled: false`, the UI alerts the user gracefully, and direct CSV export remains 100% functional.*

