"""Generate Official SIH 2026 Idea Submission PowerPoint File (.pptx) with Image Placeholders.
Strictly follows 6-slide SIH template structure with 2-column visual layout and dedicated image frames.
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def build_presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    # Colors
    NAVY = RGBColor(15, 23, 42)
    BLUE = RGBColor(30, 58, 138)
    DARK_BLUE = RGBColor(30, 64, 175)
    GREEN = RGBColor(16, 185, 129)
    WHITE = RGBColor(255, 255, 255)
    PLACEHOLDER_BG = RGBColor(241, 245, 249)
    PLACEHOLDER_BORDER = RGBColor(148, 163, 184)
    PLACEHOLDER_TEXT = RGBColor(71, 85, 105)

    blank_slide_layout = prs.slide_layouts[6]

    # Helper: Add slide header banner
    def add_header(slide, title_text, slide_num):
        banner = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(1.1))
        banner.fill.solid()
        banner.fill.fore_color.rgb = BLUE
        banner.line.color.rgb = BLUE
        
        tf = banner.text_frame
        tf.margin_left = Inches(0.8)
        tf.margin_top = Inches(0.2)
        p = tf.paragraphs[0]
        p.text = title_text.upper()
        p.font.bold = True
        p.font.size = Pt(26)
        p.font.color.rgb = WHITE
        p.font.name = "Arial"

        tag_box = slide.shapes.add_textbox(Inches(9.5), Inches(0.2), Inches(3.5), Inches(0.8))
        tf_tag = tag_box.text_frame
        p_tag = tf_tag.paragraphs[0]
        p_tag.text = "SMART INDIA HACKATHON 2026\nTeam Presentation"
        p_tag.alignment = PP_ALIGN.RIGHT
        p_tag.font.size = Pt(12)
        p_tag.font.bold = True
        p_tag.font.color.rgb = WHITE
        p_tag.font.name = "Arial"

        footer = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(7.0), Inches(13.333), Inches(0.5))
        footer.fill.solid()
        footer.fill.fore_color.rgb = NAVY
        footer.line.color.rgb = NAVY
        
        ft_tf = footer.text_frame
        ft_tf.margin_left = Inches(0.8)
        ft_tf.margin_top = Inches(0.1)
        fp = ft_tf.paragraphs[0]
        fp.text = f"@SIH Idea Submission Template  |  Slide {slide_num} of 6"
        fp.font.size = Pt(11)
        fp.font.color.rgb = WHITE
        fp.font.name = "Arial"

    # Helper: Add Image Placeholder Box
    def add_image_placeholder(slide, left, top, width, height, title, subtitle):
        box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        box.fill.solid()
        box.fill.fore_color.rgb = PLACEHOLDER_BG
        box.line.color.rgb = PLACEHOLDER_BORDER
        box.line.width = Pt(2)

        tf = box.text_frame
        tf.margin_left = Inches(0.3)
        tf.margin_right = Inches(0.3)
        tf.margin_top = Inches(0.4)
        
        p1 = tf.paragraphs[0]
        p1.text = "📷 IMAGE PLACEHOLDER"
        p1.font.bold = True
        p1.font.size = Pt(16)
        p1.font.color.rgb = DARK_BLUE
        p1.font.name = "Arial"
        p1.alignment = PP_ALIGN.CENTER
        p1.space_after = Pt(10)

        p2 = tf.add_paragraph()
        p2.text = title
        p2.font.bold = True
        p2.font.size = Pt(14)
        p2.font.color.rgb = NAVY
        p2.font.name = "Arial"
        p2.alignment = PP_ALIGN.CENTER
        p2.space_after = Pt(6)

        p3 = tf.add_paragraph()
        p3.text = subtitle
        p3.font.size = Pt(12)
        p3.font.color.rgb = PLACEHOLDER_TEXT
        p3.font.name = "Arial"
        p3.alignment = PP_ALIGN.CENTER

    # ==================== SLIDE 1: TITLE PAGE ====================
    slide1 = prs.slides.add_slide(blank_slide_layout)
    bg1 = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = NAVY
    bg1.line.fill.background()

    tbox1 = slide1.shapes.add_textbox(Inches(0.8), Inches(0.8), Inches(11.7), Inches(2.0))
    tf1 = tbox1.text_frame
    p1 = tf1.paragraphs[0]
    p1.text = "SMART INDIA HACKATHON 2026"
    p1.font.bold = True
    p1.font.size = Pt(36)
    p1.font.color.rgb = GREEN
    p1.font.name = "Arial"

    p1_sub = tf1.add_paragraph()
    p1_sub.text = "NEXORA: AI RAILWAY TRAFFIC CONTROL & OPTIMIZATION COMMAND CENTER"
    p1_sub.font.bold = True
    p1_sub.font.size = Pt(22)
    p1_sub.font.color.rgb = WHITE
    p1_sub.font.name = "Arial"

    box_details = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(3.0), Inches(11.733), Inches(3.8))
    box_details.fill.solid()
    box_details.fill.fore_color.rgb = RGBColor(30, 41, 59)
    box_details.line.color.rgb = GREEN

    tf_d = box_details.text_frame
    tf_d.margin_left = Inches(0.5)
    tf_d.margin_top = Inches(0.4)

    fields = [
        ("Problem Statement ID:", "SIH1601 / [Your PS ID]"),
        ("Problem Statement Title:", "AI-Powered Dynamic Railway Traffic Control & Conflict-Free Dispatching"),
        ("Theme:", "Smart Automation / Transportation & Public Infrastructure"),
        ("PS Category:", "Software"),
        ("Team ID:", "[Your Team ID]"),
        ("Team Name:", "Nexora / [Registered Team Name]"),
    ]
    for label, val in fields:
        p = tf_d.add_paragraph()
        p.text = f"• {label}  {val}"
        p.font.size = Pt(17)
        p.font.color.rgb = WHITE
        p.font.name = "Arial"
        p.space_after = Pt(8)

    # Helper for 2-column text
    def add_bullet_group(tf, head, items):
        hp = tf.add_paragraph()
        hp.text = head
        hp.font.bold = True
        hp.font.size = Pt(17)
        hp.font.color.rgb = DARK_BLUE
        hp.space_after = Pt(3)
        for it in items:
            p = tf.add_paragraph()
            p.text = f"  • {it}"
            p.font.size = Pt(13)
            p.font.color.rgb = NAVY
            p.space_after = Pt(3)

    # ==================== SLIDE 2: PROPOSED SOLUTION ====================
    slide2 = prs.slides.add_slide(blank_slide_layout)
    add_header(slide2, "PROPOSED SOLUTION (Idea & Prototype)", 2)

    # Left column (Text)
    s2_box = slide2.shapes.add_textbox(Inches(0.8), Inches(1.3), Inches(7.5), Inches(5.4))
    tf2 = s2_box.text_frame

    add_bullet_group(tf2, "1. Proposed Solution Explanation:", [
        "Live Digital Twin Engine modeling Mumbai Central Line (CSMT to Thane corridor).",
        "Integrates Scikit-Learn Random Forest ML predictions for congestion risk scoring.",
        "Executes Google OR-Tools CP-SAT optimization to calculate conflict-free dispatch slots in < 150 ms.",
    ])

    add_bullet_group(tf2, "2. How It Addresses the Problem:", [
        "Replaces manual controller trial-and-error with automated, proven track dispatches.",
        "Reroutes blocked trains via interlocked crossovers (e.g. Signal S-14 Crossover).",
    ])

    add_bullet_group(tf2, "3. Innovation & Uniqueness:", [
        "Hybrid AI Architecture: Probabilistic ML Risk + Exact CP-SAT Interval Scheduling.",
        "Physics Kinematics: Dynamically computes travel times (D_edge / V_kmh).",
        "Guaranteed Zero Conflicts: Enforces 120s safety headway buffers & track locks.",
    ])

    # Right column (Image Placeholder)
    add_image_placeholder(
        slide2,
        left=Inches(8.6),
        top=Inches(1.4),
        width=Inches(4.0),
        height=Inches(5.2),
        title="[Insert Screenshot of Live Railway Network Graph]",
        subtitle="(Insert dashboard screenshot showing live train markers moving along CSMT-Thane stations and Dadar blockage visualization)"
    )

    # ==================== SLIDE 3: TECHNICAL APPROACH ====================
    slide3 = prs.slides.add_slide(blank_slide_layout)
    add_header(slide3, "TECHNICAL APPROACH & METHODOLOGY", 3)

    s3_box = slide3.shapes.add_textbox(Inches(0.8), Inches(1.3), Inches(7.5), Inches(5.4))
    tf3 = s3_box.text_frame

    add_bullet_group(tf3, "1. Technologies & Architecture Stack:", [
        "Backend Engine: Python 3.10, FastAPI, Uvicorn, Asynchronous REST Services.",
        "Optimization Engine: Google OR-Tools CP-SAT (Constraint Programming & MILP).",
        "Machine Learning: Scikit-Learn Random Forest Classifier (joblib model), Pandas.",
        "Frontend Dashboard: React 18, TypeScript, Vite, Tailwind CSS, SVG Visualizer.",
        "Graph Model: RailwayNetworkGraph supporting fast/slow lines & node topology.",
    ])

    add_bullet_group(tf3, "2. Process & Implementation Workflow:", [
        "Step 1 (Live Ticker): Updates train positions, progress %, speeds, and ETAs every 1s.",
        "Step 2 (Risk Monitor): Telemetry features trigger Random Forest inference.",
        "Step 3 (CP-SAT Solver): Solves single-occupancy interval constraints subject to safety headway.",
        "Step 4 (Live Dispatch): Reassigns tracks (Track 1 Slow), restores speeds, & clears queues.",
    ])

    add_image_placeholder(
        slide3,
        left=Inches(8.6),
        top=Inches(1.4),
        width=Inches(4.0),
        height=Inches(5.2),
        title="[Insert Architecture / Workflow Flowchart]",
        subtitle="(Insert diagram showing Data Flow: Live Telemetry -> ML Risk Model -> OR-Tools CP-SAT Solver -> Dashboard UI)"
    )

    # ==================== SLIDE 4: FEASIBILITY AND VIABILITY ====================
    slide4 = prs.slides.add_slide(blank_slide_layout)
    add_header(slide4, "FEASIBILITY AND VIABILITY", 4)

    s4_box = slide4.shapes.add_textbox(Inches(0.8), Inches(1.3), Inches(7.5), Inches(5.4))
    tf4 = s4_box.text_frame

    add_bullet_group(tf4, "1. Feasibility Analysis:", [
        "Ultra-Fast Solver: CP-SAT executes in 80ms – 250ms for real-time Control Office deployment.",
        "Non-Disruptive: Consumes standard COA/ICMS timetable JSONs without changing physical signalling.",
        "100% Verified: Passes automated end-to-end test suite across 7/7 core simulation test cases.",
    ])

    add_bullet_group(tf4, "2. Operational Challenges & Risks:", [
        "Data Latency: Transmission delays in live GPS telemetry feeds during peak rush hours.",
        "Loco Pilot Brakes: Sudden emergency stops or signal overshoots by train drivers.",
    ])

    add_bullet_group(tf4, "3. Mitigation Strategies:", [
        "Rolling-Horizon Replanning: Re-optimizes schedule every 10–30s for position deltas.",
        "Robust Pipelines: Uses Scikit-Learn imputer & encoder pipelines for missing data resilience.",
        "Safety Headway Buffers: Enforces mandatory 120s safety headway buffers.",
    ])

    add_image_placeholder(
        slide4,
        left=Inches(8.6),
        top=Inches(1.4),
        width=Inches(4.0),
        height=Inches(5.2),
        title="[Insert CP-SAT Solver Execution Screenshot]",
        subtitle="(Insert screenshot of OR-Tools CP-SAT Optimization Panel showing Measured Solve Time in ms & Status: OPTIMAL)"
    )

    # ==================== SLIDE 5: IMPACT AND BENEFITS ====================
    slide5 = prs.slides.add_slide(blank_slide_layout)
    add_header(slide5, "IMPACT AND BENEFITS", 5)

    s5_box = slide5.shapes.add_textbox(Inches(0.8), Inches(1.3), Inches(7.5), Inches(5.4))
    tf5 = s5_box.text_frame

    add_bullet_group(tf5, "1. Target Audience Impact (Traffic Controllers):", [
        "Provides Controllers with instant, conflict-free rerouting recommendations.",
        "Significantly reduces Section Controller workload during major track disruptions.",
    ])

    add_bullet_group(tf5, "2. Social Benefits:", [
        "Saves millions of commuter hours daily across busy suburban networks (CSMT-Thane).",
        "Reduces platform overcrowding and boarding accidents during rush hour delays.",
    ])

    add_bullet_group(tf5, "3. Economic & Environmental Benefits:", [
        "Throughput Recovery: Boosts line throughput capacity by +35% to +50% post-incident.",
        "Fuel & Power Savings: Cuts diesel/electric power loss from outer-signal idling.",
        "Carbon Footprint Cut: Reduces idle locomotive carbon emissions across freight & passenger lines.",
    ])

    add_image_placeholder(
        slide5,
        left=Inches(8.6),
        top=Inches(1.4),
        width=Inches(4.0),
        height=Inches(5.2),
        title="[Insert Before vs After Metrics Screenshot]",
        subtitle="(Insert screenshot of Before vs After Optimization Panel showing Throughput Gain, Delay Cut, & 100% Conflict Clearance)"
    )

    # ==================== SLIDE 6: RESEARCH AND REFERENCES ====================
    slide6 = prs.slides.add_slide(blank_slide_layout)
    add_header(slide6, "RESEARCH AND REFERENCES", 6)

    s6_box = slide6.shapes.add_textbox(Inches(0.8), Inches(1.3), Inches(7.5), Inches(5.4))
    tf6 = s6_box.text_frame

    add_bullet_group(tf6, "1. Indian Railways Domain Standards:", [
        "Indian Railways General & Subsidiary Rules (G&SR) — Interlocking Regulations.",
        "Integrated Coaching Management System (ICMS) & Control Office Application (COA) Specifications.",
    ])

    add_bullet_group(tf6, "2. Algorithmic Research:", [
        "Google OR-Tools Constraint Programming (CP-SAT) Framework Documentation.",
        "Scikit-Learn Machine Learning Pipelines: Random Forest Ensemble Learning for Delay Risk.",
        "Railway Graph Theory: Dynamic Conflict Detection & Track Resource Allocation Models.",
    ])

    add_bullet_group(tf6, "3. Prototype Verification & Repository:", [
        "Live Dashboard URL: http://localhost:5173  |  Backend API: http://127.0.0.1:8000/api",
        "Automated Test Suite: sih_traintraffic/tests/test_end_to_end_validation.py (Passed 7/7).",
    ])

    add_image_placeholder(
        slide6,
        left=Inches(8.6),
        top=Inches(1.4),
        width=Inches(4.0),
        height=Inches(5.2),
        title="[Insert Event Log & Repository Screenshot]",
        subtitle="(Insert screenshot of Live System Event Log panel showing streaming audit trail and GitHub Repository commits)"
    )

    # Save presentation
    output_path = "Nexora_SIH2026_Idea_Submission.pptx"
    prs.save(output_path)
    print(f"Successfully generated PowerPoint file with image placeholders: {output_path}")

if __name__ == "__main__":
    build_presentation()
