# RosterIQ: Technical Presentation Speaker Notes

**Presentation Title:** RosterIQ — Smart Rostering. Better Teams.  
**Audience:** DataStraw Technical Evaluators, Engineering Interviewers, and Hiring Managers  
**Total Target Timing:** 2 minutes 15 seconds to 2 minutes 30 seconds  
**Deliverable File:** `docs/presentation/RosterIQ_DataStraw_Demo.pptx`

---

## Slide 1: The Problem and My Approach
- **Slide Title:** RosterIQ — Smart Rostering. Better Teams.
- **Header Tag:** OPERATIONAL PROBLEM & ENGINEERING APPROACH
- **Target Duration:** ~25 seconds

### Spoken Script (First-Person Narration)
> "Good morning everyone. I’m presenting RosterIQ, an intelligent multi-brand workforce scheduling engine that I built to solve the core challenges outlined in the DataStraw evaluation.
>
> In real-world e-commerce operations, multiple D2C brands operate across distinct hours—some are 8-by-5, others 24-by-7. Staffing cannot be handled with simple calendar invites because employees belong to operational pods, hold multi-tiered skills, have planned leaves and strict daily hour limits. Spreadsheets collapse at scale because workforce scheduling is fundamentally a constrained resource optimization problem, not a static grid.
>
> As shown on the slide, my architecture enables single-shift multi-brand allocation—for example, Asha can support Brand A in the morning and Brand B in the afternoon without exceeding working hours. My approach follows a strict 5-step pipeline: relational modeling, demand resolution, deterministic allocation, zero-trust validation, and manager-approved CP-SAT optimization.
>
> Next, let’s examine how this pipeline is implemented across the system architecture."

---

## Slide 2: System Architecture
- **Slide Title:** System Architecture
- **Header Tag:** TECHNICAL STACK, PIPELINE & RELATIONAL MODEL
- **Target Duration:** ~30 seconds

### Spoken Script (First-Person Narration)
> "Here is the end-to-end architecture and data model.
>
> On the frontend, I developed a responsive single-page application using React 19, TypeScript, Vite, and Tailwind CSS. The backend is built with FastAPI and SQLAlchemy 2.0, enforcing strict Role-Based Access Control across five distinct roles: Admin, Operations Manager, Pod Lead, Brand User, and Employee. For persistence, I chose PostgreSQL on Neon Serverless with Alembic migrations, deployed via Render and Vercel.
>
> Notice the strict separation of concerns in the execution pipeline: When a manager requests roster generation, the system resolves demand and filters employee eligibility deterministically. It executes greedy allocation and runs an independent validator before drafting the roster to PostgreSQL.
>
> A core design choice I made: CP-SAT optimization does *not* run unconditionally during initial generation. Roster generation is fast and deterministic, running in under 30 milliseconds. CP-SAT is invoked only on-demand when managers choose to resolve staffing conflicts."

---

## Slide 3: Scheduling Algorithm and Conflict Resolution
- **Slide Title:** How RosterIQ Generates and Validates a Roster
- **Header Tag:** TWO-STAGE HYBRID SCHEDULING & CONFLICT RESOLUTION
- **Target Duration:** ~35 seconds

### Spoken Script (First-Person Narration)
> "Now let’s look at the scheduling engine, which operates in two distinct stages.
>
> Stage 1 is the Deterministic Greedy Generator. It expands operating patterns, weekday schedules, and holiday calendars—such as closed, normal, or reduced rules—into discrete slot demands. It deterministically sorts slots, evaluates primary brand assignments, checks skills and leaves, and searches same-pod backups. If no qualified employee exists within the pod, it explicitly records an uncovered shortage conflict rather than fabricating coverage.
>
> Stage 2 is the Manager-Triggered OR-Tools CP-SAT Resolver. When disruptions occur, managers trigger the solver. CP-SAT models the problem with boolean decision variables and optimizes against five prioritized objectives: first, maximizing filled positions; second, satisfying full demand intervals; third, minimizing cross-pod friction; fourth, minimizing roster churn; and fifth, respecting employee preferences.
>
> In the concrete scenario shown: Asha covers two brands in one shift. Ben is on approved medical leave, leaving Brand A open. Chen in Pod 2 has the required skill, but because cross-pod assignment breaks team boundaries, CP-SAT recommends Chen and requires Operations Manager authorization before applying the change."

---

## Slide 4: Performance Benchmarks and Testing Evidence
- **Slide Title:** Performance, Validation and Testing
- **Header Tag:** AUDITED BENCHMARKS, CP-SAT MEASUREMENTS & TEST SUITE
- **Target Duration:** ~25 seconds

### Spoken Script (First-Person Narration)
> "Here are our empirical benchmarks and testing evidence.
>
> On our Core Demo dataset of 36 employees across 4 pods and 18 brand-processes, RosterIQ generates a complete 30-day monthly roster of 470 allocations in 28.9 milliseconds, with independent validation completing in 4.1 milliseconds, achieving 100% coverage with zero conflicts.
>
> For scientific rigor, I report Medium and Large datasets exactly as measured: in Medium, 465 allocations were generated with 775 conflicts, representing 37.5% coverage. In Large, 1,853 allocations were made with 1,237 conflicts. These datasets represent intentionally under-resourced stress scenarios, proving that our scheduler surfaces legitimate shortages rather than making invalid assignments.
>
> For CP-SAT, a 10-candidate single-slot disruption achieved OPTIMAL status in 48.5 milliseconds. In our audit, I retracted earlier multi-slot rows due to duplicate variable keys in the benchmark script.
>
> On reliability, our backend has 109 passing pytest tests with zero regressions, covering authentication, RBAC, migrations, greedy generation, validation rules, and solver logic."

---

## Slide 5: Operational Workflow, Decisions and Next Steps
- **Slide Title:** From Automated Scheduling to Human-Controlled Operations
- **Header Tag:** OPERATIONAL LIFECYCLE, GOVERNANCE & ROADMAP
- **Target Duration:** ~25 seconds

### Spoken Script (First-Person Narration)
> "To conclude, real-world workforce scheduling is about balancing automation with human operational agency.
>
> The top of the slide outlines our complete 9-step operational lifecycle: from configuring brands and skills, generating rosters, reviewing leaves, running CP-SAT resolutions, to publishing locked schedules and exporting to Google Sheets.
>
> I established a clear boundary: the engine automates demand resolution, eligibility, deterministic allocation, and solver optimization. However, human managers retain explicit control over roster publication, cross-pod reassignments, and leave approvals.
>
> In terms of next steps, I plan to harden configuration hash caching, complete end-to-end credential onboarding workflows, provide natural language conflict explanations, and move large-scale background generation to Redis worker queues.
>
> As stated: RosterIQ makes workforce scheduling more reliable, explainable, and adaptable while keeping critical operational decisions under human control.
>
> I’ll now transition to the live deployed application to demonstrate these workflows in action."

---

## Summary of Timing and Cues
| Slide | Focus | Spoken Timing | Transition Cue |
|---|---|---|---|
| **Slide 1** | Problem & Multi-Allocation | 0:00 - 0:25 (25s) | *"Next, let's examine how this pipeline is implemented..."* |
| **Slide 2** | Architecture & Pipeline | 0:25 - 0:55 (30s) | *"Now let's look at the scheduling engine..."* |
| **Slide 3** | Greedy Generator & CP-SAT | 0:55 - 1:30 (35s) | *"Here are our empirical benchmarks and testing evidence..."* |
| **Slide 4** | Benchmarks & Pytest Suite | 1:30 - 1:55 (25s) | *"To conclude, real-world workforce scheduling..."* |
| **Slide 5** | Governance & Live Transition | 1:55 - 2:20 (25s) | *"I'll now transition to the live deployed application..."* |
| **Total** | | **2m 20s** | Seamless handoff to browser demo |

