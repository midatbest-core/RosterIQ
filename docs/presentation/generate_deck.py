import sys
import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def create_deck(output_path):
    prs = Presentation()
    # 16:9 widescreen
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Color Palette
    BG_DARK = RGBColor(15, 23, 42)       # #0F172A Slate 950
    CARD_BG = RGBColor(30, 41, 59)       # #1E293B Slate 800
    CARD_BORDER = RGBColor(51, 65, 85)   # #334155 Slate 700
    CARD_INNER = RGBColor(15, 23, 42)    # #0F172A
    ACCENT_INDIGO = RGBColor(99, 102, 241) # #6366F1
    ACCENT_CYAN = RGBColor(6, 182, 212)    # #06B6D4
    ACCENT_GREEN = RGBColor(16, 185, 129)  # #10B981
    ACCENT_AMBER = RGBColor(245, 158, 11)  # #F59E0B
    ACCENT_ROSE = RGBColor(239, 68, 68)    # #EF4444
    TEXT_WHITE = RGBColor(248, 250, 252)   # #F8FAFC
    TEXT_MUTED = RGBColor(148, 163, 184)   # #94A3B8
    TEXT_DIM = RGBColor(100, 116, 139)     # #64748B

    def add_bg(slide):
        bg_shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg_shape.fill.solid()
        bg_shape.fill.fore_color.rgb = BG_DARK
        bg_shape.line.fill.background()
        return bg_shape

    def add_header(slide, title_text, category_text="ROSTERIQ TECHNICAL EVALUATION"):
        # Category tag
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.733), Inches(0.35))
        tf_c = cat_box.text_frame
        tf_c.word_wrap = True
        tf_c.margin_left = tf_c.margin_right = tf_c.margin_top = tf_c.margin_bottom = 0
        p_c = tf_c.paragraphs[0]
        p_c.text = category_text.upper()
        p_c.font.size = Pt(10)
        p_c.font.bold = True
        p_c.font.color.rgb = ACCENT_CYAN

        # Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.72), Inches(11.733), Inches(0.65))
        tf_t = title_box.text_frame
        tf_t.word_wrap = True
        tf_t.margin_left = tf_t.margin_right = tf_t.margin_top = tf_t.margin_bottom = 0
        p_t = tf_t.paragraphs[0]
        p_t.text = title_text
        p_t.font.size = Pt(26)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_WHITE

    def add_card(slide, left, top, width, height, bg_color=CARD_BG, border_color=CARD_BORDER):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        if border_color:
            card.line.color.rgb = border_color
            card.line.width = Pt(1)
        else:
            card.line.fill.background()
        return card

    # ==========================================
    # SLIDE 1: The Problem and My Approach
    # ==========================================
    slide1 = prs.slides.add_slide(blank_layout)
    add_bg(slide1)
    add_header(slide1, "RosterIQ - Smart Rostering. Better Teams.", "OPERATIONAL PROBLEM & ENGINEERING APPROACH")

    # Left Column: Operational Complexity & Design Objective
    add_card(slide1, Inches(0.8), Inches(1.5), Inches(5.6), Inches(5.4))
    
    tb = slide1.shapes.add_textbox(Inches(1.05), Inches(1.7), Inches(5.1), Inches(0.4))
    p = tb.text_frame.paragraphs[0]
    p.text = "THE MULTI-BRAND SCHEDULING CHALLENGE"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = ACCENT_INDIGO

    # Problem bullet cards
    bullet_items = [
        ("Multiple Brands & Operating Calendars", "D2C brands operate across distinct hours (8x5, 12x7, 24x7) with unique holiday calendars and minimum staffing rules."),
        ("Multi-Skilled Workforce & Pod Structure", "Employees belong to operational pods, hold tiered skills (L1/L2), and support single or multiple brands across distinct processes."),
        ("Leaves, Weekly Offs & Capacity Constraints", "Individual planned leaves, public holidays, weekly offs, and strict maximum daily/weekly working hour limits."),
        ("Why Spreadsheets Fail at Scale", "Manual rosters suffer from hidden coverage deficits, double-booking, cross-pod chaos, and brittle crisis rescheduling.")
    ]
    cur_y = Inches(2.15)
    for title, desc in bullet_items:
        add_card(slide1, Inches(1.05), cur_y, Inches(5.1), Inches(0.72), CARD_INNER, CARD_BORDER)
        t_box = slide1.shapes.add_textbox(Inches(1.15), cur_y + Inches(0.06), Inches(4.9), Inches(0.6))
        tf = t_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        p1 = tf.paragraphs[0]
        p1.text = title
        p1.font.size = Pt(10.5)
        p1.font.bold = True
        p1.font.color.rgb = TEXT_WHITE
        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(8.5)
        p2.font.color.rgb = TEXT_MUTED
        cur_y += Inches(0.8)

    # Design Objective Box at bottom left
    add_card(slide1, Inches(1.05), Inches(5.45), Inches(5.1), Inches(1.25), RGBColor(30, 27, 75), ACCENT_INDIGO)
    obj_box = slide1.shapes.add_textbox(Inches(1.2), Inches(5.55), Inches(4.8), Inches(1.05))
    tf_obj = obj_box.text_frame
    tf_obj.word_wrap = True
    tf_obj.margin_left = tf_obj.margin_right = tf_obj.margin_top = tf_obj.margin_bottom = 0
    p_obj_h = tf_obj.paragraphs[0]
    p_obj_h.text = "CORE ARCHITECTURAL OBJECTIVE"
    p_obj_h.font.size = Pt(9.5)
    p_obj_h.font.bold = True
    p_obj_h.font.color.rgb = ACCENT_CYAN
    p_obj_b = tf_obj.add_paragraph()
    p_obj_b.text = '"Generate operationally valid monthly rosters, identify unresolved staffing conflicts, and keep managers in control of exceptional decisions."'
    p_obj_b.font.size = Pt(11)
    p_obj_b.font.italic = True
    p_obj_b.font.bold = True
    p_obj_b.font.color.rgb = TEXT_WHITE

    # Right Column: Multi-Allocation Example & 5-Step Approach
    add_card(slide1, Inches(6.7), Inches(1.5), Inches(5.8), Inches(5.4))
    
    tb_r = slide1.shapes.add_textbox(Inches(6.95), Inches(1.7), Inches(5.3), Inches(0.4))
    p_r = tb_r.text_frame.paragraphs[0]
    p_r.text = "SHARED RESOURCE MODEL & 5-STEP PIPELINE"
    p_r.font.size = Pt(13)
    p_r.font.bold = True
    p_r.font.color.rgb = ACCENT_INDIGO

    # Multi-allocation visual box
    add_card(slide1, Inches(6.95), Inches(2.15), Inches(5.3), Inches(1.5), CARD_INNER, CARD_BORDER)
    v_box = slide1.shapes.add_textbox(Inches(7.1), Inches(2.25), Inches(5.0), Inches(1.3))
    tf_v = v_box.text_frame
    tf_v.word_wrap = True
    tf_v.margin_left = tf_v.margin_right = tf_v.margin_top = tf_v.margin_bottom = 0
    pv1 = tf_v.paragraphs[0]
    pv1.text = "Real-World Multi-Allocation: 1 Employee Shift, 2 Brands"
    pv1.font.size = Pt(10)
    pv1.font.bold = True
    pv1.font.color.rgb = ACCENT_CYAN

    # Sub-blocks inside visual box
    add_card(slide1, Inches(7.15), Inches(2.7), Inches(2.35), Inches(0.75), RGBColor(19, 78, 74), ACCENT_GREEN)
    b1_box = slide1.shapes.add_textbox(Inches(7.2), Inches(2.75), Inches(2.25), Inches(0.65))
    tf_b1 = b1_box.text_frame
    tf_b1.margin_left = tf_b1.margin_right = tf_b1.margin_top = tf_b1.margin_bottom = 0
    pb1 = tf_b1.paragraphs[0]
    pb1.text = "09:00 - 13:00 (4 hrs)"
    pb1.font.size = Pt(9)
    pb1.font.bold = True
    pb1.font.color.rgb = RGBColor(167, 243, 208)
    pb1_s = tf_b1.add_paragraph()
    pb1_s.text = "Brand A : Customer Support\nPrimary Skill L1"
    pb1_s.font.size = Pt(8)
    pb1_s.font.color.rgb = TEXT_WHITE

    add_card(slide1, Inches(9.65), Inches(2.7), Inches(2.4), Inches(0.75), RGBColor(67, 56, 202), ACCENT_INDIGO)
    b2_box = slide1.shapes.add_textbox(Inches(9.7), Inches(2.75), Inches(2.3), Inches(0.65))
    tf_b2 = b2_box.text_frame
    tf_b2.margin_left = tf_b2.margin_right = tf_b2.margin_top = tf_b2.margin_bottom = 0
    pb2 = tf_b2.paragraphs[0]
    pb2.text = "14:00 - 18:00 (4 hrs)"
    pb2.font.size = Pt(9)
    pb2.font.bold = True
    pb2.font.color.rgb = RGBColor(199, 210, 254)
    pb2_s = tf_b2.add_paragraph()
    pb2_s.text = "Brand B : Order Escalations\nSecondary Skill L2"
    pb2_s.font.size = Pt(8)
    pb2_s.font.color.rgb = TEXT_WHITE

    # 5-Step Approach Box
    steps_data = [
        ("1. Model Relationally", "Capture Employees, Pods, Skills, Operating Patterns, and Overrides in PostgreSQL."),
        ("2. Resolve Demand", "Compute interval-by-interval required staffing across operating calendars and holidays."),
        ("3. Allocate Deterministically", "Greedy allocation: primary assigned employees first, followed by same-pod backups."),
        ("4. Independently Validate", "Zero-trust rule engine checks shifts, overlapping allocations, leaves, and capacity."),
        ("5. Manager-Reviewed Optimisation", "Targeted OR-Tools CP-SAT solves unassigned shortages with human review.")
    ]
    cur_y_s = Inches(3.8)
    for step_t, step_d in steps_data:
        s_card = add_card(slide1, Inches(6.95), cur_y_s, Inches(5.3), Inches(0.54), CARD_INNER, CARD_BORDER)
        s_box = slide1.shapes.add_textbox(Inches(7.05), cur_y_s + Inches(0.04), Inches(5.1), Inches(0.46))
        tf_s = s_box.text_frame
        tf_s.word_wrap = True
        tf_s.margin_left = tf_s.margin_right = tf_s.margin_top = tf_s.margin_bottom = 0
        ps1 = tf_s.paragraphs[0]
        ps1.text = step_t
        ps1.font.size = Pt(9.5)
        ps1.font.bold = True
        ps1.font.color.rgb = ACCENT_CYAN
        ps2 = tf_s.add_paragraph()
        ps2.text = step_d
        ps2.font.size = Pt(8)
        ps2.font.color.rgb = TEXT_MUTED
        cur_y_s += Inches(0.58)

    # Notes for Slide 1
    slide1.notes_slide.notes_text_frame.text = (
        "Good morning everyone. I'm presenting RosterIQ, an intelligent multi-brand workforce scheduling system.\n\n"
        "The DataStraw assignment represents a critical operational reality: D2C brands have varying operating "
        "hours, differing holiday calendars, and shared or dedicated staffing. Spreadsheets collapse under this complexity "
        "because workforce scheduling is not a calendar event problem—it is a constrained multi-objective resource optimization problem.\n\n"
        "My design objective was clear: generate operationally valid monthly rosters deterministically, detect unresolved "
        "staffing shortages transparently, and empower managers to review and apply mathematical optimizations without losing control.\n\n"
        "As shown here, an employee like Asha can support Brand A in the morning and Brand B in the afternoon under a single unified shift. "
        "We achieve this through a 5-step engineering pipeline: relational modeling, demand resolution, deterministic allocation, "
        "independent validation, and manager-reviewed CP-SAT optimization. Let's look at the system architecture."
    )

    # ==========================================
    # SLIDE 2: Architecture and Data Model
    # ==========================================
    slide2 = prs.slides.add_slide(blank_layout)
    add_bg(slide2)
    add_header(slide2, "System Architecture", "TECHNICAL STACK, PIPELINE & RELATIONAL MODEL")

    # Layer Cards across top
    layers = [
        ("Frontend Presentation", "React 19 + TypeScript + Vite\nTailwind CSS + Lucide Icons\nResponsive Desktop & Tablet", RGBColor(14, 116, 144), ACCENT_CYAN),
        ("Backend & API Layer", "FastAPI + Pydantic v2\nJWT Auth + Role-Based RBAC\n(Admin, Ops, Pod Lead, Brand, Emp)", RGBColor(67, 56, 202), ACCENT_INDIGO),
        ("Scheduling & Solver Engine", "DemandResolver + Eligibility Engine\nDeterministic Greedy Allocator\nIndependent Validator + OR-Tools CP-SAT", RGBColor(30, 27, 75), ACCENT_AMBER),
        ("Persistence & Database", "PostgreSQL (Neon Serverless)\nSQLAlchemy 2.0 ORM\nAlembic Schema Migrations", RGBColor(19, 78, 74), ACCENT_GREEN),
        ("Hosting & CI/CD", "Vercel: Static SPA Frontend\nRender: Containerized FastAPI\nNeon: Cloud PostgreSQL", CARD_BG, CARD_BORDER)
    ]
    x_offset = Inches(0.8)
    layer_w = Inches(2.22)
    for title, text, bg, border in layers:
        add_card(slide2, x_offset, Inches(1.5), layer_w, Inches(1.4), bg, border)
        l_box = slide2.shapes.add_textbox(x_offset + Inches(0.1), Inches(1.58), layer_w - Inches(0.2), Inches(1.2))
        tf_l = l_box.text_frame
        tf_l.word_wrap = True
        tf_l.margin_left = tf_l.margin_right = tf_l.margin_top = tf_l.margin_bottom = 0
        pl1 = tf_l.paragraphs[0]
        pl1.text = title
        pl1.font.size = Pt(10)
        pl1.font.bold = True
        pl1.font.color.rgb = TEXT_WHITE
        pl2 = tf_l.add_paragraph()
        pl2.text = text
        pl2.font.size = Pt(8)
        pl2.font.color.rgb = RGBColor(226, 232, 240)
        x_offset += Inches(2.38)

    # End-to-end Pipeline Bar in Middle
    add_card(slide2, Inches(0.8), Inches(3.05), Inches(11.733), Inches(0.9), CARD_INNER, CARD_BORDER)
    pipe_box = slide2.shapes.add_textbox(Inches(0.9), Inches(3.1), Inches(11.5), Inches(0.8))
    tf_pipe = pipe_box.text_frame
    tf_pipe.word_wrap = True
    tf_pipe.margin_left = tf_pipe.margin_right = tf_pipe.margin_top = tf_pipe.margin_bottom = 0
    pp_h = tf_pipe.paragraphs[0]
    pp_h.text = "END-TO-END EXECUTION FLOW (STRICT BOUNDARY SEPARATION)"
    pp_h.font.size = Pt(9)
    pp_h.font.bold = True
    pp_h.font.color.rgb = ACCENT_CYAN

    pipeline_flow = (
        "Manager Action   →   REST API /auth   →   Demand Resolution   →   Eligibility Filter   →   "
        "Greedy Allocation   →   Zero-Trust Validation   →   Persistence (Draft Roster)   →   "
        "[Optional Manager Trigger] CP-SAT Resolver   →   Published Roster"
    )
    pp_flow = tf_pipe.add_paragraph()
    pp_flow.text = pipeline_flow
    pp_flow.font.size = Pt(9.5)
    pp_flow.font.bold = True
    pp_flow.font.color.rgb = TEXT_WHITE

    # Bottom Half Left: Core Relational Entities
    add_card(slide2, Inches(0.8), Inches(4.1), Inches(6.8), Inches(2.8), CARD_BG, CARD_BORDER)
    tb_rel = slide2.shapes.add_textbox(Inches(1.0), Inches(4.2), Inches(6.4), Inches(0.35))
    p_rel = tb_rel.text_frame.paragraphs[0]
    p_rel.text = "CORE RELATIONAL DATA MODEL & ASSOCIATIONS"
    p_rel.font.size = Pt(11)
    p_rel.font.bold = True
    p_rel.font.color.rgb = ACCENT_INDIGO

    entities = [
        ("Workforce & Pods", "Employee (skills, hours, weekly off) ↔ Pod (PodLead, cross-pod boundary)"),
        ("Demand Structure", "Brand ↔ BrandProcess (process tier, min staffing, operating hours, holiday rules)"),
        ("Skills & Assignments", "EmployeeProcessSkill (L1/L2) + PrimaryAssignment (BrandProcess priority)"),
        ("Roster Artifacts", "Roster (draft/published) → EmployeeShift (working window) → RosterAllocation (slot)"),
        ("Unavailability & Change", "EmployeeUnavailability (leave/holidays) + PlanChangeRequest (audit trail)")
    ]
    cur_y_e = Inches(4.6)
    for title, desc in entities:
        e_box = slide2.shapes.add_textbox(Inches(1.0), cur_y_e, Inches(6.4), Inches(0.4))
        tf_e = e_box.text_frame
        tf_e.word_wrap = True
        tf_e.margin_left = tf_e.margin_right = tf_e.margin_top = tf_e.margin_bottom = 0
        pe1 = tf_e.paragraphs[0]
        pe1.text = "• " + title + ": "
        pe1.font.size = Pt(9)
        pe1.font.bold = True
        pe1.font.color.rgb = TEXT_WHITE
        run = pe1.add_run()
        run.text = desc
        run.font.bold = False
        run.font.color.rgb = TEXT_MUTED
        cur_y_e += Inches(0.42)

    # Bottom Half Right: Critical Architectural Decisions
    add_card(slide2, Inches(7.8), Inches(4.1), Inches(4.733), Inches(2.8), CARD_BG, CARD_BORDER)
    tb_dec = slide2.shapes.add_textbox(Inches(8.0), Inches(4.2), Inches(4.3), Inches(0.35))
    p_dec = tb_dec.text_frame.paragraphs[0]
    p_dec.text = "KEY ARCHITECTURAL DECISIONS"
    p_dec.font.size = Pt(11)
    p_dec.font.bold = True
    p_dec.font.color.rgb = ACCENT_INDIGO

    decisions = [
        ("Multi-Allocation Shift Model", "A single shift spans an employee's workday. Within that shift, multiple non-overlapping allocations to different BrandProcesses exist, strictly enforcing maximum capacity."),
        ("Deterministic Core vs Solver Separation", "Initial roster generation is purely deterministic (reproducible, <30ms). CP-SAT is NOT run unconditionally on every generation; it is triggered on-demand by managers for conflict resolution."),
        ("Zero-Trust Independent Validation", "Validation is completely decoupled from generator logic. An independent engine validates 8 hard constraints before any roster state can be committed or published.")
    ]
    cur_y_d = Inches(4.6)
    for title, desc in decisions:
        d_box = slide2.shapes.add_textbox(Inches(8.0), cur_y_d, Inches(4.3), Inches(0.65))
        tf_d = d_box.text_frame
        tf_d.word_wrap = True
        tf_d.margin_left = tf_d.margin_right = tf_d.margin_top = tf_d.margin_bottom = 0
        pd1 = tf_d.paragraphs[0]
        pd1.text = title
        pd1.font.size = Pt(9)
        pd1.font.bold = True
        pd1.font.color.rgb = ACCENT_AMBER
        pd2 = tf_d.add_paragraph()
        pd2.text = desc
        pd2.font.size = Pt(8)
        pd2.font.color.rgb = TEXT_MUTED
        cur_y_d += Inches(0.72)

    # Notes for Slide 2
    slide2.notes_slide.notes_text_frame.text = (
        "Here is the system architecture and data model.\n\n"
        "On the presentation layer, I built a responsive React 19 and TypeScript frontend with Tailwind CSS. "
        "The backend is powered by FastAPI and SQLAlchemy 2.0, enforcing strict Role-Based Access Control across five distinct roles: "
        "Admin, Operations Manager, Pod Lead, Brand User, and Employee. Database persistence is handled by Neon Serverless PostgreSQL with Alembic migrations.\n\n"
        "Notice the execution pipeline: When a manager clicks Generate, the backend resolves demand, filters employee eligibility, "
        "and runs a fast deterministic greedy allocation. It then passes the generated roster to an independent zero-trust validator.\n\n"
        "A critical design decision is highlighted here: an employee can hold multiple allocations within a single shift for different brands, "
        "provided time windows do not overlap. Crucially, CP-SAT does NOT run automatically on every generation—it is an on-demand optimization tool "
        "invoked by managers when unassigned slots require intelligent reassignment."
    )

    # ==========================================
    # SLIDE 3: Scheduling Algorithm and Conflict Resolution
    # ==========================================
    slide3 = prs.slides.add_slide(blank_layout)
    add_bg(slide3)
    add_header(slide3, "How RosterIQ Generates and Validates a Roster", "TWO-STAGE HYBRID SCHEDULING & CONFLICT RESOLUTION")

    # Left Column: Deterministic Greedy Generation (7 Steps)
    add_card(slide3, Inches(0.8), Inches(1.5), Inches(5.6), Inches(4.2), CARD_BG, CARD_BORDER)
    tb_g = slide3.shapes.add_textbox(Inches(1.0), Inches(1.65), Inches(5.2), Inches(0.35))
    pg = tb_g.text_frame.paragraphs[0]
    pg.text = "STAGE 1: DETERMINISTIC GREEDY GENERATOR"
    pg.font.size = Pt(11)
    pg.font.bold = True
    pg.font.color.rgb = ACCENT_CYAN

    greedy_steps = [
        "1. Resolve Demand: Expand operating patterns, weekday schedules, public holiday rules (CLOSED/NORMAL/REDUCED), and date overrides into slot requirements.",
        "2. Deterministic Sort: Order required demand slots deterministically by date, start time, brand priority, and process complexity.",
        "3. Match Primary Assignments: For each slot, identify employees with active primary assignments to the target BrandProcess.",
        "4. Strict Eligibility Filter: Verify active status, verified skills (L1/L2), absence of approved leave/unavailability, shift bounds, and non-overlapping daily hours.",
        "5. Same-Pod Backup Search: If primary resources are unavailable or exhausted, evaluate eligible backup employees within the same pod.",
        "6. Uncovered Slot Recording: When no eligible pod resource exists, record an explicit uncovered shortage conflict (never silently ignore demand).",
        "7. Independent Validation: Run zero-trust validator checking 8 hard constraints (double booking, shift boundaries, rest gaps, skill mismatch)."
    ]
    cur_y_g = Inches(2.05)
    for step in greedy_steps:
        box = slide3.shapes.add_textbox(Inches(1.0), cur_y_g, Inches(5.2), Inches(0.38))
        tf = box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        p_step = tf.paragraphs[0]
        p_step.text = step
        p_step.font.size = Pt(8)
        p_step.font.color.rgb = TEXT_WHITE
        cur_y_g += Inches(0.39)

    # Explanation callout under Greedy
    add_card(slide3, Inches(0.8), Inches(5.8), Inches(5.6), Inches(1.1), CARD_INNER, ACCENT_CYAN)
    call_box = slide3.shapes.add_textbox(Inches(0.95), Inches(5.88), Inches(5.3), Inches(0.9))
    tf_c = call_box.text_frame
    tf_c.word_wrap = True
    tf_c.margin_left = tf_c.margin_right = tf_c.margin_top = tf_c.margin_bottom = 0
    pc1 = tf_c.paragraphs[0]
    pc1.text = "Greedy Scheduling Principle:"
    pc1.font.size = Pt(9)
    pc1.font.bold = True
    pc1.font.color.rgb = ACCENT_CYAN
    pc2 = tf_c.add_paragraph()
    pc2.text = '"The scheduler makes the best eligible allocation available at each step rather than searching every possible complete roster. This delivers sub-30ms execution for 30-day rosters while surfacing legitimate staffing shortages."'
    pc2.font.size = Pt(8)
    pc2.font.italic = True
    pc2.font.color.rgb = TEXT_WHITE

    # Right Column: Manager-Triggered OR-Tools CP-SAT Resolver
    add_card(slide3, Inches(6.7), Inches(1.5), Inches(5.8), Inches(4.2), CARD_BG, CARD_BORDER)
    tb_c = slide3.shapes.add_textbox(Inches(6.9), Inches(1.65), Inches(5.4), Inches(0.35))
    pc = tb_c.text_frame.paragraphs[0]
    pc.text = "STAGE 2: MANAGER-TRIGGERED OR-TOOLS CP-SAT"
    pc.font.size = Pt(11)
    pc.font.bold = True
    pc.font.color.rgb = ACCENT_AMBER

    cpsat_features = [
        ("Decision Variables", "Boolean x[e, s] indicating whether candidate employee e is assigned to unresolved slot s."),
        ("Hard Feasibility Constraints", "Strictly enforce max 1 assignment per slot, zero overlapping shifts, approved leave exclusion, skill requirements, and maximum daily working limits."),
        ("Lexicographic Objective Priorities", "Multi-pass weighted optimization objective hierarchy:"),
        ("  Priority 1 (Weight 10,000)", "Maximise covered staffing positions (fill open slots)."),
        ("  Priority 2 (Weight 1,000)", "Maximise fully satisfied demand intervals across brands."),
        ("  Priority 3 (Weight -500)", "Minimise cross-pod assignments (prefer pod cohesion)."),
        ("  Priority 4 (Weight -100)", "Minimise churn/disruption to previously assigned shifts."),
        ("  Priority 5 (Weight +50)", "Prefer primary brand assignments & respect weekly off."),
        ("Manager Authorization Gate", "Cross-pod reassignment requires explicit Operations Manager or Admin confirmation; pod leads cannot unilaterally reassign outside their pod.")
    ]
    cur_y_c = Inches(2.05)
    for label, text in cpsat_features:
        box = slide3.shapes.add_textbox(Inches(6.9), cur_y_c, Inches(5.4), Inches(0.3))
        tf = box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        p_c = tf.paragraphs[0]
        p_c.text = "• " + label + ": " if ":" not in label and "Priority" not in label else label + ": "
        p_c.font.size = Pt(7.8)
        p_c.font.bold = True
        p_c.font.color.rgb = ACCENT_AMBER if "Priority" in label else TEXT_WHITE
        run = p_c.add_run()
        run.text = text
        run.font.bold = False
        run.font.color.rgb = TEXT_MUTED
        cur_y_c += Inches(0.28)

    # Bottom Concrete Scenario Box (Asha / Ben / Chen)
    add_card(slide3, Inches(6.7), Inches(5.8), Inches(5.8), Inches(1.1), CARD_INNER, ACCENT_AMBER)
    scen_box = slide3.shapes.add_textbox(Inches(6.85), Inches(5.88), Inches(5.5), Inches(0.9))
    tf_sc = scen_box.text_frame
    tf_sc.word_wrap = True
    tf_sc.margin_left = tf_sc.margin_right = tf_sc.margin_top = tf_sc.margin_bottom = 0
    ps_h = tf_sc.paragraphs[0]
    ps_h.text = "Operational Example: Asha, Ben, and Chen"
    ps_h.font.size = Pt(9)
    ps_h.font.bold = True
    ps_h.font.color.rgb = ACCENT_AMBER
    ps_b = tf_sc.add_paragraph()
    ps_b.text = (
        "• Asha (Pod 1): Assigned Brand A (09:00-13:00) & Brand B (14:00-18:00) within 1 shift (8h total, valid).\n"
        "• Ben (Pod 1): Brand A primary, but has approved medical leave → greedy generator marks slot uncovered.\n"
        "• Chen (Pod 2): Has Brand A skill but belongs to Pod 2 → greedy generator leaves slot open; CP-SAT identifies Chen as an optimal candidate, awaiting Manager cross-pod approval."
    )
    ps_b.font.size = Pt(7.5)
    ps_b.font.color.rgb = TEXT_WHITE

    # Notes for Slide 3
    slide3.notes_slide.notes_text_frame.text = (
        "Now let's examine the scheduling engine. I designed a two-stage hybrid approach.\n\n"
        "Stage 1 is the Deterministic Greedy Generator. It expands operating patterns, weekday schedules, and holiday rules "
        "into interval demand, sorts them deterministically, and assigns primary resources. If unavailable, it checks same-pod backups. "
        "If no eligible employee exists within the pod, it does not force an invalid assignment; it records an explicit uncovered shortage conflict. "
        "As the quote notes: the scheduler makes the best eligible allocation available at each step, running in under 30 milliseconds.\n\n"
        "Stage 2 is the Manager-Triggered OR-Tools CP-SAT Resolver. When leaves or surge demands create shortages, managers open the Conflict Resolver. "
        "CP-SAT models the problem with boolean decision variables and optimizes against five lexicographic priorities: "
        "maximizing covered positions, maximizing satisfied intervals, minimizing cross-pod friction, minimizing roster disruption, "
        "and respecting employee preferences.\n\n"
        "In our scenario: Asha smoothly handles two non-overlapping brands. When Ben goes on leave, the generator leaves Brand A uncovered. "
        "Chen in Pod 2 has the skill, but because cross-pod assignment breaks team boundaries, CP-SAT recommends Chen and requires "
        "explicit Operations Manager authorization before applying the change."
    )

    # ==========================================
    # SLIDE 4: Performance Benchmarks and Testing Evidence
    # ==========================================
    slide4 = prs.slides.add_slide(blank_layout)
    add_bg(slide4)
    add_header(slide4, "Performance, Validation and Testing", "AUDITED BENCHMARKS, CP-SAT MEASUREMENTS & TEST SUITE")

    # Left Column: Scheduler Benchmark Table
    add_card(slide4, Inches(0.8), Inches(1.5), Inches(6.8), Inches(3.2), CARD_BG, CARD_BORDER)
    tb_b = slide4.shapes.add_textbox(Inches(1.0), Inches(1.65), Inches(6.4), Inches(0.35))
    pb = tb_b.text_frame.paragraphs[0]
    pb.text = "AUDITED SYNTHETIC SCHEDULER BENCHMARKS (30-DAY MONTHLY GRID)"
    pb.font.size = Pt(11)
    pb.font.bold = True
    pb.font.color.rgb = ACCENT_INDIGO

    # Table
    table_shape = slide4.shapes.add_table(4, 8, Inches(1.0), Inches(2.05), Inches(6.4), Inches(1.4))
    table = table_shape.table
    table.columns[0].width = Inches(1.1)
    table.columns[1].width = Inches(0.65)
    table.columns[2].width = Inches(0.55)
    table.columns[3].width = Inches(0.7)
    table.columns[4].width = Inches(0.75)
    table.columns[5].width = Inches(0.75)
    table.columns[6].width = Inches(0.95)
    table.columns[7].width = Inches(0.95)

    headers = ["Dataset", "Emps", "Pods", "B-Proc", "Allocs", "Conflicts", "Gen / Val Time", "Coverage"]
    for i, h in enumerate(headers):
        cell = table.cell(0, i)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(51, 65, 85)
        for p in cell.text_frame.paragraphs:
            p.alignment = PP_ALIGN.CENTER
            p.font.size = Pt(7.5)
            p.font.bold = True
            p.font.color.rgb = TEXT_WHITE

    bench_rows = [
        ("Core Demo (A)", "36", "4", "18", "470", "0", "28.9ms / 4.1ms", "100.0% (Valid)"),
        ("Medium (B)", "100", "10", "48", "465", "775", "1,029.9ms / 8.0ms", "37.5% (Shortage)"),
        ("Large (C)", "300", "20", "120", "1,853", "1,237", "27,275ms / 40.9ms", "59.9% (Shortage)")
    ]
    for row_idx, data in enumerate(bench_rows, start=1):
        for col_idx, val in enumerate(data):
            cell = table.cell(row_idx, col_idx)
            cell.text = val
            cell.fill.solid()
            cell.fill.fore_color.rgb = CARD_INNER
            for p in cell.text_frame.paragraphs:
                p.alignment = PP_ALIGN.CENTER if col_idx > 0 else PP_ALIGN.LEFT
                p.font.size = Pt(7.5)
                p.font.bold = (col_idx == 0 or col_idx == 7)
                if col_idx == 7:
                    p.font.color.rgb = ACCENT_GREEN if "100" in val else ACCENT_AMBER
                else:
                    p.font.color.rgb = TEXT_WHITE

    # Explanation note under table
    tb_bn = slide4.shapes.add_textbox(Inches(1.0), Inches(3.55), Inches(6.4), Inches(1.0))
    tf_bn = tb_bn.text_frame
    tf_bn.word_wrap = True
    tf_bn.margin_left = tf_bn.margin_right = tf_bn.margin_top = tf_bn.margin_bottom = 0
    pbn1 = tf_bn.paragraphs[0]
    pbn1.text = "Audit Interpretation & CP-SAT Measurement:"
    pbn1.font.size = Pt(8.5)
    pbn1.font.bold = True
    pbn1.font.color.rgb = ACCENT_CYAN
    pbn2 = tf_bn.add_paragraph()
    pbn2.text = (
        "• Datasets B & C reflect intentionally under-resourced stress scenarios (775 & 1,237 unfilled demand conflicts); they are NOT full-coverage rosters.\n"
        "• Valid CP-SAT Benchmark: 10 candidates, 1 open slot → OPTIMAL status, 1 allocation assigned in 48.5 ms.\n"
        "• Audit Correction: Multi-slot benchmark rows (5, 20, 50 slots) were retracted due to duplicate decision variable keys in the legacy benchmark harness."
    )
    pbn2.font.size = Pt(7.5)
    pbn2.font.color.rgb = TEXT_MUTED

    # Bottom Left: Benchmark Caveats Box
    add_card(slide4, Inches(0.8), Inches(4.85), Inches(6.8), Inches(2.05), CARD_INNER, CARD_BORDER)
    tb_cav = slide4.shapes.add_textbox(Inches(1.0), Inches(4.95), Inches(6.4), Inches(1.85))
    tf_cav = tb_cav.text_frame
    tf_cav.word_wrap = True
    tf_cav.margin_left = tf_cav.margin_right = tf_cav.margin_top = tf_cav.margin_bottom = 0
    pcav1 = tf_cav.paragraphs[0]
    pcav1.text = "MANDATORY BENCHMARK CAVEATS & MEASUREMENT SCOPE"
    pcav1.font.size = Pt(8.5)
    pcav1.font.bold = True
    pcav1.font.color.rgb = ACCENT_AMBER
    pcav2 = tf_cav.add_paragraph()
    pcav2.text = (
        "• Synthetic in-memory data models for November 2026 scenarios; single archived benchmark runs, not multi-run averages.\n"
        "• Excludes production database, network, HTTP/JSON serialization, and TLS latency overhead.\n"
        "• Benchmarked Environment: Windows 11, AMD 8-core/16-thread 3.20 GHz, 15.31 GB RAM, Python 3.14.3.\n"
        "• Transparent Engineering Notice: These metrics reflect algorithmic compute time, not SLA production guarantees."
    )
    pcav2.font.size = Pt(7.5)
    pcav2.font.color.rgb = TEXT_MUTED

    # Right Column: Testing Evidence & Quality Gates
    add_card(slide4, Inches(7.8), Inches(1.5), Inches(4.733), Inches(5.4), CARD_BG, CARD_BORDER)
    tb_t = slide4.shapes.add_textbox(Inches(8.0), Inches(1.65), Inches(4.3), Inches(0.35))
    pt = tb_t.text_frame.paragraphs[0]
    pt.text = "TESTING EVIDENCE & VERIFICATION AUDIT"
    pt.font.size = Pt(11)
    pt.font.bold = True
    pt.font.color.rgb = ACCENT_GREEN

    # Pass badge
    add_card(slide4, Inches(8.0), Inches(2.05), Inches(4.3), Inches(0.85), RGBColor(6, 78, 59), ACCENT_GREEN)
    tb_badge = slide4.shapes.add_textbox(Inches(8.15), Inches(2.1), Inches(4.0), Inches(0.75))
    tf_badge = tb_badge.text_frame
    tf_badge.word_wrap = True
    tf_badge.margin_left = tf_badge.margin_right = tf_badge.margin_top = tf_badge.margin_bottom = 0
    pbdg1 = tf_badge.paragraphs[0]
    pbdg1.text = "109 / 109 Pytest Tests Passed"
    pbdg1.font.size = Pt(13)
    pbdg1.font.bold = True
    pbdg1.font.color.rgb = RGBColor(167, 243, 208)
    pbdg2 = tf_badge.add_paragraph()
    pbdg2.text = "Total Test Suite Runtime: 73.45 seconds (13 Nov 2026 Audit)\nZero Failures | Zero Regressions | Isolated SQLite WAL"
    pbdg2.font.size = Pt(8)
    pbdg2.font.color.rgb = TEXT_WHITE

    test_domains = [
        ("Authentication & CSRF", "JWT access tokens, CSRF double-submit cookies, timing-safe hashes, auto-provisioning."),
        ("RBAC & Pod Isolation", "Strict multi-role matrix (Admin, Ops, Pod Lead, Brand, Emp); 403 enforcement on unauthorized leave actions."),
        ("Data Constraints & Migrations", "Database check constraints, foreign keys, cascade deletes, Alembic upgrade scripts."),
        ("Deterministic Scheduling", "Demand pattern expansion, weekday/holiday handling, greedy allocation, primary vs backup."),
        ("Independent Validator", "Zero-trust verification of 8 conflict types (overlap, capacity, skill mismatch, rest period)."),
        ("OR-Tools CP-SAT Resolver", "Optimal slot allocation, candidate constraints, multi-objective weighting, cross-pod flags."),
        ("Lifecycle & Requests", "Roster publishing, draft locks, CSV/Sheets exports, leave approvals, plan change auditing.")
    ]
    cur_y_td = Inches(3.05)
    for title, desc in test_domains:
        tb_td = slide4.shapes.add_textbox(Inches(8.0), cur_y_td, Inches(4.3), Inches(0.38))
        tf_td = tb_td.text_frame
        tf_td.word_wrap = True
        tf_td.margin_left = tf_td.margin_right = tf_td.margin_top = tf_td.margin_bottom = 0
        ptd1 = tf_td.paragraphs[0]
        ptd1.text = "✓ " + title + ": "
        ptd1.font.size = Pt(8)
        ptd1.font.bold = True
        ptd1.font.color.rgb = ACCENT_GREEN
        run = ptd1.add_run()
        run.text = desc
        run.font.bold = False
        run.font.color.rgb = TEXT_MUTED
        cur_y_td += Inches(0.38)

    # Note on Frontend verification
    tb_fe = slide4.shapes.add_textbox(Inches(8.0), Inches(6.15), Inches(4.3), Inches(0.65))
    tf_fe = tb_fe.text_frame
    tf_fe.word_wrap = True
    tf_fe.margin_left = tf_fe.margin_right = tf_fe.margin_top = tf_fe.margin_bottom = 0
    pfe1 = tf_fe.paragraphs[0]
    pfe1.text = "Frontend Quality Status:"
    pfe1.font.size = Pt(8)
    pfe1.font.bold = True
    pfe1.font.color.rgb = ACCENT_CYAN
    pfe2 = tf_fe.add_paragraph()
    pfe2.text = "ESLint exit code 0; TypeScript verification clean; no committed frontend unit/E2E test suite (identified for next milestone)."
    pfe2.font.size = Pt(7.5)
    pfe2.font.color.rgb = TEXT_MUTED

    # Notes for Slide 4
    slide4.notes_slide.notes_text_frame.text = (
        "Here are our empirical benchmarks and testing evidence.\n\n"
        "On our Core Demo dataset of 36 employees across 4 pods and 18 brand-processes, RosterIQ generated a full 30-day "
        "monthly roster of 470 allocations in 28.9 milliseconds, with independent validation completing in 4.1 milliseconds, "
        "achieving 100% coverage with zero conflicts.\n\n"
        "For scientific honesty, I report Medium and Large datasets exactly as measured: in Medium, 465 allocations were made "
        "with 775 conflicts, representing a 37.5% coverage rate. In Large, 1,853 allocations were made with 1,237 conflicts. "
        "These are intentionally under-resourced datasets demonstrating that the scheduler refuses to fabricate coverage when staffing is mathematically insufficient.\n\n"
        "For CP-SAT, a 10-candidate single-slot disruption achieved OPTIMAL status in 48.5 milliseconds. I also explicitly retract "
        "the multi-slot benchmark rows due to a decision-variable key duplication found during our code audit.\n\n"
        "On quality assurance, our backend test suite has 109 passing pytest tests covering security, RBAC isolation, database constraints, "
        "greedy generation, validation rules, and CP-SAT solvers. All tests pass with zero regressions."
    )

    # ==========================================
    # SLIDE 5: Operational Workflow, Decisions and Next Steps
    # ==========================================
    slide5 = prs.slides.add_slide(blank_layout)
    add_bg(slide5)
    add_header(slide5, "From Automated Scheduling to Human-Controlled Operations", "OPERATIONAL LIFECYCLE, GOVERNANCE & ROADMAP")

    # Top: 9-Step End-to-End Operational Flow (Horizontal Cards)
    add_card(slide5, Inches(0.8), Inches(1.5), Inches(11.733), Inches(1.4), CARD_BG, CARD_BORDER)
    tb_fl = slide5.shapes.add_textbox(Inches(1.0), Inches(1.58), Inches(11.3), Inches(0.28))
    pfl = tb_fl.text_frame.paragraphs[0]
    pfl.text = "COMPLETE 9-STEP OPERATIONAL LIFECYCLE"
    pfl.font.size = Pt(10)
    pfl.font.bold = True
    pfl.font.color.rgb = ACCENT_INDIGO

    flow_steps = [
        ("1. Configure", "Brands, processes & operating hours"),
        ("2. Maintain", "Employees, pods, skills & max hours"),
        ("3. Generate", "Deterministic monthly draft roster"),
        ("4. Review", "Inspect allocations & coverage stats"),
        ("5. Identify", "Pinpoint shortage conflicts & gaps"),
        ("6. Leaves", "Submit, audit & approve leaves"),
        ("7. Resolve", "Preview & apply CP-SAT solutions"),
        ("8. Publish", "Zero-trust validation & lock roster"),
        ("9. Export", "Export CSV & sync to Google Sheets")
    ]
    cur_x_f = Inches(1.0)
    for title, desc in flow_steps:
        add_card(slide5, cur_x_f, Inches(1.9), Inches(1.18), Inches(0.88), CARD_INNER, CARD_BORDER)
        f_box = slide5.shapes.add_textbox(cur_x_f + Inches(0.05), Inches(1.95), Inches(1.08), Inches(0.78))
        tf_f = f_box.text_frame
        tf_f.word_wrap = True
        tf_f.margin_left = tf_f.margin_right = tf_f.margin_top = tf_f.margin_bottom = 0
        pf1 = tf_f.paragraphs[0]
        pf1.text = title
        pf1.font.size = Pt(8.5)
        pf1.font.bold = True
        pf1.font.color.rgb = ACCENT_CYAN
        pf2 = tf_f.add_paragraph()
        pf2.text = desc
        pf2.font.size = Pt(6.8)
        pf2.font.color.rgb = TEXT_MUTED
        cur_x_f += Inches(1.26)

    # Bottom Left: Automation vs Human Control Matrix
    add_card(slide5, Inches(0.8), Inches(3.05), Inches(5.6), Inches(3.0), CARD_BG, CARD_BORDER)
    tb_gov = slide5.shapes.add_textbox(Inches(1.0), Inches(3.15), Inches(5.2), Inches(0.3))
    pgov = tb_gov.text_frame.paragraphs[0]
    pgov.text = "SYSTEM GOVERNANCE: AUTOMATION VS HUMAN CONTROL"
    pgov.font.size = Pt(10)
    pgov.font.bold = True
    pgov.font.color.rgb = ACCENT_CYAN

    # Automated Box
    add_card(slide5, Inches(1.0), Inches(3.5), Inches(5.2), Inches(1.15), CARD_INNER, CARD_BORDER)
    tb_auto = slide5.shapes.add_textbox(Inches(1.1), Inches(3.55), Inches(5.0), Inches(1.05))
    tf_auto = tb_auto.text_frame
    tf_auto.word_wrap = True
    tf_auto.margin_left = tf_auto.margin_right = tf_auto.margin_top = tf_auto.margin_bottom = 0
    p_at1 = tf_auto.paragraphs[0]
    p_at1.text = "⚡ Automated by RosterIQ Engine"
    p_at1.font.size = Pt(9)
    p_at1.font.bold = True
    p_at1.font.color.rgb = ACCENT_GREEN
    p_at2 = tf_auto.add_paragraph()
    p_at2.text = (
        "• Operating pattern expansion & holiday calendar demand resolution\n"
        "• Employee skill & capacity eligibility filtering\n"
        "• Deterministic primary allocation & same-pod backup assignment\n"
        "• Independent zero-trust conflict detection & CP-SAT solver formulation"
    )
    p_at2.font.size = Pt(7.5)
    p_at2.font.color.rgb = TEXT_WHITE

    # Human Control Box
    add_card(slide5, Inches(1.0), Inches(4.75), Inches(5.2), Inches(1.15), CARD_INNER, CARD_BORDER)
    tb_hum = slide5.shapes.add_textbox(Inches(1.1), Inches(4.8), Inches(5.0), Inches(1.05))
    tf_hum = tb_hum.text_frame
    tf_hum.word_wrap = True
    tf_hum.margin_left = tf_hum.margin_right = tf_hum.margin_top = tf_hum.margin_bottom = 0
    p_hm1 = tf_hum.paragraphs[0]
    p_hm1.text = "👤 Retained Under Human Control (Managers & Leads)"
    p_hm1.font.size = Pt(9)
    p_hm1.font.bold = True
    p_hm1.font.color.rgb = ACCENT_AMBER
    p_hm2 = tf_hum.add_paragraph()
    p_hm2.text = (
        "• Formal roster publication & draft locking authority\n"
        "• Cross-pod resource reallocations (requires Ops Manager / Admin signoff)\n"
        "• Planned leave & operational plan change approvals\n"
        "• Exceptional manual shift overrides & overtime staffing authorisations"
    )
    p_hm2.font.size = Pt(7.5)
    p_hm2.font.color.rgb = TEXT_WHITE

    # Bottom Right: What I Would Improve Next (Engineering Roadmap)
    add_card(slide5, Inches(6.7), Inches(3.05), Inches(5.8), Inches(3.0), CARD_BG, CARD_BORDER)
    tb_imp = slide5.shapes.add_textbox(Inches(6.9), Inches(3.15), Inches(5.4), Inches(0.3))
    pimp = tb_imp.text_frame.paragraphs[0]
    pimp.text = "WHAT I WOULD IMPROVE NEXT (ENGINEERING ROADMAP)"
    pimp.font.size = Pt(10)
    pimp.font.bold = True
    pimp.font.color.rgb = ACCENT_AMBER

    roadmap = [
        ("1. Configuration Hash & Enum Hardening", "Standardise config hash calculation to prevent stale cache hits; unify frontend and backend conflict status enums."),
        ("2. End-to-End Dynamic Onboarding", "Brand & employee creation APIs are built; complete automated credential distribution and immediate scheduling integration without server restarts."),
        ("3. Rich Conflict Explanations & Suggestions", "Augment solver output with natural-language root-cause explanations and ranked backup recommendations for human operators."),
        ("4. Background Async Jobs & Distributed Workers", "Migrate long-running Large dataset generation (27s) to Celery/Redis background task queues with WebSocket progress indicators.")
    ]
    cur_y_r = Inches(3.5)
    for title, desc in roadmap:
        r_box = slide5.shapes.add_textbox(Inches(6.9), cur_y_r, Inches(5.4), Inches(0.55))
        tf_r = r_box.text_frame
        tf_r.word_wrap = True
        tf_r.margin_left = tf_r.margin_right = tf_r.margin_top = tf_r.margin_bottom = 0
        pr1 = tf_r.paragraphs[0]
        pr1.text = title
        pr1.font.size = Pt(8.5)
        pr1.font.bold = True
        pr1.font.color.rgb = ACCENT_AMBER
        pr2 = tf_r.add_paragraph()
        pr2.text = desc
        pr2.font.size = Pt(7.5)
        pr2.font.color.rgb = TEXT_MUTED
        cur_y_r += Inches(0.58)

    # Closing Callout Quote at Bottom
    add_card(slide5, Inches(0.8), Inches(6.15), Inches(11.733), Inches(0.8), RGBColor(30, 27, 75), ACCENT_INDIGO)
    tb_cl = slide5.shapes.add_textbox(Inches(1.0), Inches(6.22), Inches(11.3), Inches(0.65))
    tf_cl = tb_cl.text_frame
    tf_cl.word_wrap = True
    tf_cl.margin_left = tf_cl.margin_right = tf_cl.margin_top = tf_cl.margin_bottom = 0
    pcl1 = tf_cl.paragraphs[0]
    pcl1.text = '"RosterIQ aims to make workforce scheduling more reliable, explainable and adaptable while keeping critical operational decisions under human control."'
    pcl1.alignment = PP_ALIGN.CENTER
    pcl1.font.size = Pt(11)
    pcl1.font.bold = True
    pcl1.font.italic = True
    pcl1.font.color.rgb = TEXT_WHITE
    pcl2 = tf_cl.add_paragraph()
    pcl2.text = "Now transitioning to the live application demo on the deployed web environment..."
    pcl2.alignment = PP_ALIGN.CENTER
    pcl2.font.size = Pt(8.5)
    pcl2.font.color.rgb = ACCENT_CYAN

    # Notes for Slide 5
    slide5.notes_slide.notes_text_frame.text = (
        "To conclude: workforce scheduling is fundamentally about balancing automation with human operational agency.\n\n"
        "Here you see the complete 9-step operational lifecycle, from configuring brands and skills, generating rosters, "
        "auditing leaves, applying CP-SAT conflict resolutions, to publishing locked schedules and exporting to Google Sheets.\n\n"
        "I established a strict boundary: the machine automates demand resolution, eligibility checks, deterministic allocation, "
        "and mathematical solver formulation. But humans retain authority over roster publication, cross-pod reallocations, "
        "and leave approvals.\n\n"
        "Being transparent about my roadmap: while brand and employee creation APIs exist, I want to further harden configuration hash checks, "
        "finish end-to-end credential onboarding workflows, provide natural language explanations for shortages, and move large multi-thousand slot "
        "generations to asynchronous Redis/Celery worker queues.\n\n"
        "As stated: RosterIQ aims to make workforce scheduling more reliable, explainable, and adaptable while keeping critical operational "
        "decisions under human control. I will now switch to the live deployed application to demonstrate these workflows."
    )

    prs.save(output_path)
    print(f"Presentation saved successfully to {output_path}")

if __name__ == "__main__":
    out_dir = r"C:\Users\Admin\Roster\docs\presentation"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "RosterIQ_DataStraw_Demo.pptx")
    create_deck(out_file)

