"""Master Resume data structures, tailoring engine, ATS keyword matcher, and exporters."""

from __future__ import annotations

import base64
import copy
import json
import logging
import math
import os
import re
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any
import pymupdf

logger = logging.getLogger(__name__)


@dataclass
class BulletPoint:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    text: str = ""
    enabled: bool = True


@dataclass
class ResumeEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    subtitle: str = ""
    date_range: str = ""
    location: str = ""
    gpa: str = ""
    coursework: str = ""
    skills_text: str = ""
    bullets: list[BulletPoint] = field(default_factory=list)
    enabled: bool = True


@dataclass
class ResumeSection:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: str = "experience"
    title: str = "Experience"
    entries: list[ResumeEntry] = field(default_factory=list)
    enabled: bool = True


@dataclass
class ContactInfo:
    name: str = ""
    title: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""
    website: str = ""


@dataclass
class MasterResume:
    contact: ContactInfo = field(default_factory=ContactInfo)
    summary: str = ""
    summary_enabled: bool = False
    sections: list[ResumeSection] = field(default_factory=list)
    profiles: dict[str, dict[str, Any]] = field(default_factory=dict)


def create_sample_master_resume() -> MasterResume:
    # Create sample master resume matching SpaceX GNC format.
    contact = ContactInfo(
        name="Alex Morgan",
        title="Guidance, Navigation, and Control Engineer",
        email="alex.morgan@utexas.edu",
        phone="(512) 555-0199",
        location="Austin, TX",
        linkedin="linkedin.com/in/alexmorgan-aero",
        github="github.com/alexmorgan",
        website="alexmorgan.space",
    )
    summary = ""

    # Section 1: Education
    sec_edu = ResumeSection(
        id="sec_edu", type="education", title="EDUCATION", enabled=True
    )
    ed1 = ResumeEntry(
        id="edu_1",
        title="Bachelor of Science, Aerospace Engineering Honors",
        subtitle="The University of Texas at Austin",
        date_range="December 2026",
        gpa="3.94 / 4.00",
        coursework="Orbital Mechanics, Spacecraft Dynamics & Control, Flight Mechanics, Numerical Methods, Feedback Control Systems, Aerodynamics",
        enabled=True,
    )
    sec_edu.entries = [ed1]

    # Section 2: Experience
    sec_exp = ResumeSection(
        id="sec_exp", type="experience", title="WORK EXPERIENCE", enabled=True
    )
    e1 = ResumeEntry(
        id="exp_1",
        title="Guidance, Navigation, and Control Intern",
        subtitle="Space Exploration Technologies (SpaceX)",
        date_range="May 2025 - August 2025",
        enabled=True,
        bullets=[
            BulletPoint(
                id="b1",
                text="Designed and validated 6-DOF entry guidance Monte Carlo simulations in C++ and Python, analyzing trajectory dispersions across 10,000+ flight runs.",
                enabled=True,
            ),
            BulletPoint(
                id="b2",
                text="Implemented quaternion-based attitude estimation filters integrating IMU and star tracker telemetry with extended Kalman filters.",
                enabled=True,
            ),
            BulletPoint(
                id="b3",
                text="Bench-tested reaction control thruster firing logic in hardware-in-the-loop (HIL) simulators, reducing attitude error settling time by 18%.",
                enabled=True,
            ),
        ],
    )
    e2 = ResumeEntry(
        id="exp_2",
        title="Flight Software Engineering Intern",
        subtitle="Relativity Space",
        date_range="June 2024 - August 2024",
        enabled=True,
        bullets=[
            BulletPoint(
                id="b4",
                text="Developed deterministic telemetry packet parsers and real-time state logging daemon deployed on rocket stage avionics bus.",
                enabled=True,
            ),
            BulletPoint(
                id="b5",
                text="Automated regression verification suites for stage separation dynamics, catching 4 critical timing anomalies prior to static fire.",
                enabled=True,
            ),
        ],
    )
    sec_exp.entries = [e1, e2]

    # Section 3: Projects
    sec_proj = ResumeSection(
        id="sec_proj", type="projects", title="PROJECTS", enabled=True
    )
    p1 = ResumeEntry(
        id="proj_1",
        title="Texas Rocket Engineering Lab (TREL)",
        subtitle="Avionics & Simulation Lead",
        date_range="2023 - Present",
        enabled=True,
        bullets=[
            BulletPoint(
                id="b6",
                text="Architected primary flight computer software stack for 30,000 ft altitude sounding rocket using embedded Linux and C++.",
                enabled=True,
            ),
            BulletPoint(
                id="b7",
                text="Engineered automated trajectory reconstruction pipeline from raw flash logs, reducing flight data analysis turnaround from 3 days to 15 minutes.",
                enabled=True,
            ),
        ],
    )
    sec_proj.entries = [p1]

    # Section 4: Organization
    sec_org = ResumeSection(
        id="sec_org",
        type="organization",
        title="ORGANIZATIONAL EXPERIENCE",
        enabled=True,
    )
    o1 = ResumeEntry(
        id="org_1",
        title="Lead Simulation Mentor",
        subtitle="AIAA Student Branch",
        date_range="2024 - Present",
        enabled=True,
        bullets=[
            BulletPoint(
                id="b8",
                text="Directed weekly numerical simulation workshops covering orbital transfers and feedback control loops for 45 undergraduate engineering students.",
                enabled=True,
            ),
        ],
    )
    sec_org.entries = [o1]

    # Section 5: Skills
    sec_skills = ResumeSection(
        id="sec_skills",
        type="skills",
        title="ADDITIONAL SKILLS AND LANGUAGES",
        enabled=True,
    )
    s1 = ResumeEntry(
        id="skill_1",
        title="Simulation & Analysis",
        skills_text="C++, Python, MATLAB, Simulink, ROS 2, PyMuPDF, NumPy, SciPy, FreeCAD, Linux/POSIX",
        enabled=True,
    )
    s2 = ResumeEntry(
        id="skill_2",
        title="Engineering Domains",
        skills_text="Orbital Mechanics, Kalman Filtering, 6-DOF Trajectory Simulation, Attitude Determination (ADCS), PID/LQR Control",
        enabled=True,
    )
    sec_skills.entries = [s1, s2]

    # Section 6: Accomplishments
    sec_acc = ResumeSection(
        id="sec_acc", type="accomplishments", title="ACCOMPLISHMENTS", enabled=True
    )
    a1 = ResumeEntry(
        id="acc_1",
        title="Honors & Publications",
        date_range="2024",
        enabled=True,
        bullets=[
            BulletPoint(
                id="b9",
                text="1st Place, National AIAA Undergraduate Spacecraft Design Competition (Team Lead).",
                enabled=True,
            ),
            BulletPoint(
                id="b10",
                text="University of Texas Engineering Honors Scholar (Top 5% of Engineering Class).",
                enabled=True,
            ),
        ],
    )
    sec_acc.entries = [a1]

    return MasterResume(
        contact=contact,
        summary=summary,
        summary_enabled=False,
        sections=[sec_edu, sec_exp, sec_proj, sec_org, sec_skills, sec_acc],
        profiles={},
    )


def resume_to_dict(resume: MasterResume) -> dict[str, Any]:
    # Convert MasterResume object to serializable dictionary.
    return asdict(resume)


def resume_from_dict(d: dict[str, Any] | MasterResume) -> MasterResume:
    # Deserialize dictionary into MasterResume object with fallback key support.
    if isinstance(d, MasterResume):
        return d
    contact_d = d.get("contact")
    if not isinstance(contact_d, dict):
        contact_d = {}

    contact = ContactInfo(
        name=str(contact_d.get("name") or d.get("name", "")),
        title=str(contact_d.get("title") or d.get("title", "")),
        email=str(contact_d.get("email") or d.get("email", "")),
        phone=str(contact_d.get("phone") or d.get("phone", "")),
        location=str(contact_d.get("location") or d.get("location", "")),
        linkedin=str(contact_d.get("linkedin") or d.get("linkedin", "")),
        github=str(contact_d.get("github") or d.get("github", "")),
        website=str(contact_d.get("website") or d.get("website", "")),
    )

    sum_enabled = d.get("include_summary")
    if sum_enabled is None:
        sum_enabled = bool(d.get("summary_enabled", False))
    else:
        sum_enabled = bool(sum_enabled)

    sections: list[ResumeSection] = []
    for s in d.get("sections", []):
        entries: list[ResumeEntry] = []
        for e in s.get("entries", []):
            raw_bullets = e.get("bullets", [])
            bullets = [
                BulletPoint(**b) if isinstance(b, dict) else b for b in raw_bullets
            ]
            entries.append(
                ResumeEntry(
                    id=str(e.get("id", "")),
                    title=str(e.get("title", "")),
                    subtitle=str(e.get("organization") or e.get("subtitle", "")),
                    date_range=str(e.get("dates") or e.get("date_range", "")),
                    location=str(e.get("location", "")),
                    gpa=str(e.get("gpa", "")),
                    coursework=str(e.get("coursework", "")),
                    skills_text=str(e.get("skills_text", "")),
                    bullets=bullets,
                    enabled=bool(e.get("enabled", True)),
                )
            )
        sections.append(
            ResumeSection(
                id=str(s.get("id", "")),
                type=str(s.get("type", "custom")),
                title=str(s.get("title", "Section")),
                entries=entries,
                enabled=bool(s.get("enabled", True)),
            )
        )

    return MasterResume(
        contact=contact,
        summary=str(d.get("summary", "")),
        summary_enabled=sum_enabled,
        sections=sections,
        profiles=dict(d.get("profiles", {})),
    )


def save_resume_file(resume: MasterResume, path: str) -> None:
    # Save master resume to JSON file.
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(resume_to_dict(resume), f, indent=2)


def load_resume_file(path: str) -> MasterResume:
    # Load master resume from JSON file.
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return resume_from_dict(data)


def extract_keywords(text: str) -> set[str]:
    # Extract lowercased alphanumeric keywords from text.
    words = re.findall(r"\b[A-Za-z0-9_+#.-]{2,}\b", text.lower())
    stop_words = {
        "and",
        "the",
        "for",
        "with",
        "from",
        "that",
        "this",
        "are",
        "was",
        "were",
        "will",
        "have",
        "has",
        "had",
        "been",
        "work",
        "team",
        "using",
        "into",
    }
    return {w for w in words if w not in stop_words}


def analyze_ats_match(resume: MasterResume, job_description: str) -> dict[str, Any]:
    # Analyze keyword matching score against job description.
    job_words = extract_keywords(job_description)
    resume_text = " ".join(
        [
            resume.contact.name,
            resume.contact.title,
            resume.summary,
            " ".join(
                [
                    f"{e.title} {e.subtitle} {e.coursework} {e.skills_text} "
                    + " ".join([b.text for b in e.bullets if b.enabled])
                    for s in resume.sections
                    if s.enabled
                    for e in s.entries
                    if e.enabled
                ]
            ),
        ]
    )
    resume_words = extract_keywords(resume_text)
    if not job_words:
        return {"score": 0.0, "matched": [], "missing": []}

    matched = sorted(list(job_words & resume_words))
    missing = sorted(list(job_words - resume_words))
    score = (len(matched) / len(job_words)) * 100.0
    return {
        "score": score,
        "matched": [(kw, 1) for kw in matched],
        "missing": [(kw, 1) for kw in missing],
    }


def capture_profile_version(
    resume: MasterResume, profile_name: str, note: str = ""
) -> dict[str, Any]:
    # Record version snapshot of profile states.
    if profile_name not in resume.profiles:
        resume.profiles[profile_name] = {"history": []}
    profile_data = resume.profiles[profile_name]
    history = profile_data.setdefault("history", [])
    snapshot = {
        "id": str(uuid.uuid4())[:8],
        "note": note,
        "summary": resume.summary_enabled,
        "sections": {s.id: s.enabled for s in resume.sections},
        "entries": {e.id: e.enabled for s in resume.sections for e in s.entries},
        "bullets": {
            b.id: b.enabled
            for s in resume.sections
            for e in s.entries
            for b in e.bullets
        },
    }
    history.append(snapshot)
    return snapshot


def diff_profile_versions(
    before: dict[str, Any], after: dict[str, Any]
) -> dict[str, Any]:
    # Compare two profile snapshots and return changed items.
    diff: dict[str, Any] = {"summary": before.get("summary") != after.get("summary")}
    for key in ("sections", "entries", "bullets"):
        b_map = before.get(key, {})
        a_map = after.get(key, {})
        all_ids = set(b_map.keys()) | set(a_map.keys())
        diff[key] = {
            item_id: (b_map.get(item_id), a_map.get(item_id))
            for item_id in all_ids
            if b_map.get(item_id) != a_map.get(item_id)
        }
    return diff


def save_profile(resume: MasterResume, profile_name: str) -> None:
    # Save active profile toggle states into resume dictionary.
    selection = {
        "summary": resume.summary_enabled,
        "sections": {s.id: s.enabled for s in resume.sections},
        "entries": {e.id: e.enabled for s in resume.sections for e in s.entries},
        "bullets": {
            b.id: b.enabled
            for s in resume.sections
            for e in s.entries
            for b in e.bullets
        },
    }
    resume.profiles[profile_name] = selection


def apply_profile(resume: MasterResume, profile_name: str) -> bool:
    # Apply saved profile toggle states onto resume in place.
    if profile_name not in resume.profiles:
        return False
    state = resume.profiles[profile_name]
    if "history" in state:
        state = {k: v for k, v in state.items() if k != "history"}
    resume.summary_enabled = state.get("summary", False)

    sec_map = state.get("sections", {})
    entry_map = state.get("entries", {})
    bullet_map = state.get("bullets", {})

    for sec in resume.sections:
        if sec.id in sec_map:
            sec.enabled = sec_map[sec.id]
        for entry in sec.entries:
            if entry.id in entry_map:
                entry.enabled = entry_map[entry.id]
            for bullet in entry.bullets:
                if bullet.id in bullet_map:
                    bullet.enabled = bullet_map[bullet.id]
    return True


# --- Reference Typography Resolvers ------------------------------------------


def resolve_calibri_fonts() -> dict[str, Any]:
    # Resolve Windows Calibri, Carlito, or PyMuPDF built-in fallback fonts.
    calibri_paths = {
        "regular": r"C:\Windows\Fonts\calibri.ttf",
        "bold": r"C:\Windows\Fonts\calibrib.ttf",
        "italic": r"C:\Windows\Fonts\calibrii.ttf",
        "bold_italic": r"C:\Windows\Fonts\calibriz.ttf",
    }
    if all(os.path.exists(p) for p in calibri_paths.values()):
        return {
            "use_files": True,
            "paths": calibri_paths,
            "instances": {
                k: pymupdf.Font(fontfile=p) for k, p in calibri_paths.items()
            },
            "names": {
                "regular": "F_REG",
                "bold": "F_BOLD",
                "italic": "F_ITAL",
                "bold_italic": "F_BI",
            },
        }

    return {
        "use_files": False,
        "paths": {},
        "instances": {
            "regular": pymupdf.Font("helv"),
            "bold": pymupdf.Font("hebo"),
            "italic": pymupdf.Font("heit"),
            "bold_italic": pymupdf.Font("hebi"),
        },
        "names": {
            "regular": "helv",
            "bold": "hebo",
            "italic": "heit",
            "bold_italic": "hebi",
        },
    }


def split_into_lines(
    text: str, font: pymupdf.Font, fontsize: float, max_width: float
) -> list[str]:
    # Wrap text into line strings fitting max_width based on font metrics.
    words = text.split(" ")
    lines: list[str] = []
    current_line: list[str] = []
    for word in words:
        test_str = " ".join(current_line + [word])
        if font.text_length(test_str, fontsize=fontsize) <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                lines.append(word)
                current_line = []
    if current_line:
        lines.append(" ".join(current_line))
    return lines


# --- PDF Engine -------------------------------------------------------------


def render_resume_pdf_bytes(resume: MasterResume, font_pt: float = 11.0) -> bytes:
    # Render resume to PDF bytes using exact SpaceX GNC geometry and typography.
    doc = pymupdf.open()
    font_res = resolve_calibri_fonts()
    fonts = font_res["instances"]
    fnames = font_res["names"]

    page_width = 612.0
    page_height = 792.0
    margin_left = 54.0
    margin_right = 558.0
    content_width = 504.0
    max_y = 756.0

    scale = font_pt / 11.0
    leading_line = 13.45 * scale
    leading_bullet = 14.2 * scale

    def create_page() -> tuple[pymupdf.Page, float]:
        page = doc.new_page(width=page_width, height=page_height)
        if font_res["use_files"]:
            page.insert_font(fontname="F_REG", fontfile=font_res["paths"]["regular"])
            page.insert_font(fontname="F_BOLD", fontfile=font_res["paths"]["bold"])
            page.insert_font(fontname="F_ITAL", fontfile=font_res["paths"]["italic"])
            page.insert_font(fontname="F_BI", fontfile=font_res["paths"]["bold_italic"])
        return page, 54.0

    current_page, current_y = create_page()

    # Header: Candidate Name (Centered, 20pt Bold, Uppercase)
    name_str = (resume.contact.name or "CANDIDATE NAME").upper()
    name_w = fonts["bold"].text_length(name_str, fontsize=20.0)
    current_page.insert_text(
        pymupdf.Point(306.0 - (name_w / 2.0), 55.4),
        name_str,
        fontname=fnames["bold"],
        fontsize=20.0,
        color=(0, 0, 0),
    )

    # Contact Line 1: Phone | Email | Location (Centered, 11pt Regular)
    c1_parts = [
        p
        for p in [resume.contact.phone, resume.contact.email, resume.contact.location]
        if p.strip()
    ]
    if c1_parts:
        c1_str = " | ".join(c1_parts)
        c1_w = fonts["regular"].text_length(c1_str, fontsize=11.0)
        current_page.insert_text(
            pymupdf.Point(306.0 - (c1_w / 2.0), 73.0),
            c1_str,
            fontname=fnames["regular"],
            fontsize=11.0,
            color=(0, 0, 0),
        )

    # Contact Line 2: LinkedIn | GitHub | Website (Centered, 11pt Regular)
    c2_parts = [
        p
        for p in [
            resume.contact.linkedin,
            resume.contact.github,
            resume.contact.website,
        ]
        if p.strip()
    ]
    if c2_parts:
        c2_str = " | ".join(c2_parts)
        c2_w = fonts["regular"].text_length(c2_str, fontsize=11.0)
        current_page.insert_text(
            pymupdf.Point(306.0 - (c2_w / 2.0), 86.45),
            c2_str,
            fontname=fnames["regular"],
            fontsize=11.0,
            color=(0, 0, 0),
        )
        current_y = 110.2
    else:
        current_y = 96.0 if c1_parts else 82.0

    # Optional Summary
    if resume.summary_enabled and resume.summary.strip():
        if current_y + 40.0 > max_y:
            current_page, current_y = create_page()
        current_page.insert_text(
            pymupdf.Point(margin_left, current_y),
            "SUMMARY",
            fontname=fnames["bold"],
            fontsize=11.0,
            color=(0, 0, 0),
        )
        current_page.draw_line(
            pymupdf.Point(margin_left, current_y + 6.9),
            pymupdf.Point(margin_right, current_y + 6.9),
            color=(0, 0, 0),
            width=2.0,
        )
        current_y += 24.0
        sum_lines = split_into_lines(
            resume.summary.strip(), fonts["regular"], 11.0, content_width
        )
        for sline in sum_lines:
            if current_y > max_y:
                current_page, current_y = create_page()
            current_page.insert_text(
                pymupdf.Point(margin_left, current_y),
                sline,
                fontname=fnames["regular"],
                fontsize=11.0,
                color=(0, 0, 0),
            )
            current_y += leading_line
        current_y += 10.0

    # Sections
    for sec in resume.sections:
        if not sec.enabled:
            continue
        enabled_entries = [e for e in sec.entries if e.enabled]
        if not enabled_entries:
            continue

        if current_y + 40.0 > max_y:
            current_page, current_y = create_page()

        heading_text = sec.title.upper()
        current_page.insert_text(
            pymupdf.Point(margin_left, current_y),
            heading_text,
            fontname=fnames["bold"],
            fontsize=11.0,
            color=(0, 0, 0),
        )
        current_page.draw_line(
            pymupdf.Point(margin_left, current_y + 6.9),
            pymupdf.Point(margin_right, current_y + 6.9),
            color=(0, 0, 0),
            width=2.0,
        )
        current_y += 24.0

        for entry in enabled_entries:
            sec_type = sec.type.lower()
            if sec_type == "education":
                # Line 1: Degree (Bold, left) + Graduation Date (Bold, right-aligned)
                if current_y + 35.0 > max_y:
                    current_page, current_y = create_page()
                degree_str = entry.title
                current_page.insert_text(
                    pymupdf.Point(margin_left, current_y),
                    degree_str,
                    fontname=fnames["bold"],
                    fontsize=11.0,
                    color=(0, 0, 0),
                )
                if entry.date_range:
                    date_w = fonts["bold"].text_length(entry.date_range, fontsize=11.0)
                    current_page.insert_text(
                        pymupdf.Point(margin_right - date_w, current_y),
                        entry.date_range,
                        fontname=fnames["bold"],
                        fontsize=11.0,
                        color=(0, 0, 0),
                    )
                current_y += leading_line

                # Line 2: Institution (Italic, left)
                if entry.subtitle:
                    if current_y > max_y:
                        current_page, current_y = create_page()
                    current_page.insert_text(
                        pymupdf.Point(margin_left, current_y),
                        entry.subtitle,
                        fontname=fnames["italic"],
                        fontsize=11.0,
                        color=(0, 0, 0),
                    )
                    current_y += leading_line

                # Line 3: GPA (Bold + Regular)
                if entry.gpa:
                    if current_y > max_y:
                        current_page, current_y = create_page()
                    gpa_label = "GPA: "
                    gpa_label_w = fonts["bold"].text_length(gpa_label, fontsize=11.0)
                    current_page.insert_text(
                        pymupdf.Point(margin_left, current_y),
                        gpa_label,
                        fontname=fnames["bold"],
                        fontsize=11.0,
                        color=(0, 0, 0),
                    )
                    current_page.insert_text(
                        pymupdf.Point(margin_left + gpa_label_w, current_y),
                        entry.gpa,
                        fontname=fnames["regular"],
                        fontsize=11.0,
                        color=(0, 0, 0),
                    )
                    current_y += leading_line

                # Line 4: Relevant Coursework (Bold + Regular wrapped)
                if entry.coursework:
                    cw_prefix = "Relevant Coursework: "
                    cw_pw = fonts["bold"].text_length(cw_prefix, fontsize=11.0)
                    full_cw = cw_prefix + entry.coursework
                    cw_lines = split_into_lines(
                        full_cw, fonts["regular"], 11.0, content_width
                    )
                    for c_idx, line in enumerate(cw_lines):
                        if current_y > max_y:
                            current_page, current_y = create_page()
                        if c_idx == 0:
                            current_page.insert_text(
                                pymupdf.Point(margin_left, current_y),
                                cw_prefix,
                                fontname=fnames["bold"],
                                fontsize=11.0,
                                color=(0, 0, 0),
                            )
                            body_rest = line[len(cw_prefix) :]
                            current_page.insert_text(
                                pymupdf.Point(margin_left + cw_pw, current_y),
                                body_rest,
                                fontname=fnames["regular"],
                                fontsize=11.0,
                                color=(0, 0, 0),
                            )
                        else:
                            current_page.insert_text(
                                pymupdf.Point(margin_left, current_y),
                                line,
                                fontname=fnames["regular"],
                                fontsize=11.0,
                                color=(0, 0, 0),
                            )
                        current_y += leading_line
                current_y += 6.0

            elif sec_type in ("experience", "organization"):
                if current_y + 35.0 > max_y:
                    current_page, current_y = create_page()
                # Inline Mixed Header: Title (Bold), Organization (Bold Italic), Dates (Bold)
                x_pos = margin_left
                if entry.title and entry.subtitle:
                    t_str = f"{entry.title}, "
                    current_page.insert_text(
                        pymupdf.Point(x_pos, current_y),
                        t_str,
                        fontname=fnames["bold"],
                        fontsize=11.0,
                        color=(0, 0, 0),
                    )
                    x_pos += fonts["bold"].text_length(t_str, fontsize=11.0)
                    org_str = entry.subtitle
                    current_page.insert_text(
                        pymupdf.Point(x_pos, current_y),
                        org_str,
                        fontname=fnames["bold_italic"],
                        fontsize=11.0,
                        color=(0, 0, 0),
                    )
                    x_pos += fonts["bold_italic"].text_length(org_str, fontsize=11.0)
                    if entry.date_range:
                        d_str = f", {entry.date_range}"
                        current_page.insert_text(
                            pymupdf.Point(x_pos, current_y),
                            d_str,
                            fontname=fnames["bold"],
                            fontsize=11.0,
                            color=(0, 0, 0),
                        )
                else:
                    head_main = entry.subtitle or entry.title
                    current_page.insert_text(
                        pymupdf.Point(x_pos, current_y),
                        head_main,
                        fontname=fnames["bold_italic"],
                        fontsize=11.0,
                        color=(0, 0, 0),
                    )
                    x_pos += fonts["bold_italic"].text_length(head_main, fontsize=11.0)
                    if entry.date_range:
                        d_str = f", {entry.date_range}"
                        current_page.insert_text(
                            pymupdf.Point(x_pos, current_y),
                            d_str,
                            fontname=fnames["bold"],
                            fontsize=11.0,
                            color=(0, 0, 0),
                        )
                current_y += leading_bullet

                # Bullets
                for b in entry.bullets:
                    if not b.enabled or not b.text.strip():
                        continue
                    if current_y + 14.0 > max_y:
                        current_page, current_y = create_page()
                    current_page.draw_circle(
                        pymupdf.Point(56.2, current_y - 3.4),
                        2.1,
                        color=(0, 0, 0),
                        fill=(0, 0, 0),
                    )
                    b_lines = split_into_lines(
                        b.text.strip(), fonts["regular"], 11.0, 495.0
                    )
                    for bl in b_lines:
                        if current_y > max_y:
                            current_page, current_y = create_page()
                        current_page.insert_text(
                            pymupdf.Point(63.0, current_y),
                            bl,
                            fontname=fnames["regular"],
                            fontsize=11.0,
                            color=(0, 0, 0),
                        )
                        current_y += leading_bullet
                current_y += 6.0

            elif sec_type == "projects":
                if current_y + 35.0 > max_y:
                    current_page, current_y = create_page()
                h_parts = [entry.title]
                if entry.subtitle:
                    h_parts.append(f" - {entry.subtitle}")
                if entry.date_range:
                    h_parts.append(f", {entry.date_range}")
                p_head = "".join(h_parts)
                current_page.insert_text(
                    pymupdf.Point(margin_left, current_y),
                    p_head,
                    fontname=fnames["bold"],
                    fontsize=11.0,
                    color=(0, 0, 0),
                )
                current_y += leading_bullet

                for b in entry.bullets:
                    if not b.enabled or not b.text.strip():
                        continue
                    if current_y + 14.0 > max_y:
                        current_page, current_y = create_page()
                    current_page.draw_circle(
                        pymupdf.Point(56.2, current_y - 3.4),
                        2.1,
                        color=(0, 0, 0),
                        fill=(0, 0, 0),
                    )
                    b_lines = split_into_lines(
                        b.text.strip(), fonts["regular"], 11.0, 495.0
                    )
                    for bl in b_lines:
                        if current_y > max_y:
                            current_page, current_y = create_page()
                        current_page.insert_text(
                            pymupdf.Point(63.0, current_y),
                            bl,
                            fontname=fnames["regular"],
                            fontsize=11.0,
                            color=(0, 0, 0),
                        )
                        current_y += leading_bullet
                current_y += 6.0

            elif sec_type == "skills":
                if current_y + 20.0 > max_y:
                    current_page, current_y = create_page()
                cat_label = f"{entry.title}: "
                cat_w = fonts["bold"].text_length(cat_label, fontsize=11.0)
                body_skills = entry.skills_text or ", ".join(
                    [b.text for b in entry.bullets if b.enabled]
                )
                full_skill_str = cat_label + body_skills
                skill_lines = split_into_lines(
                    full_skill_str, fonts["regular"], 11.0, content_width
                )
                for s_idx, sline in enumerate(skill_lines):
                    if current_y > max_y:
                        current_page, current_y = create_page()
                    if s_idx == 0:
                        current_page.insert_text(
                            pymupdf.Point(margin_left, current_y),
                            cat_label,
                            fontname=fnames["bold"],
                            fontsize=11.0,
                            color=(0, 0, 0),
                        )
                        body_part = sline[len(cat_label) :]
                        current_page.insert_text(
                            pymupdf.Point(margin_left + cat_w, current_y),
                            body_part,
                            fontname=fnames["regular"],
                            fontsize=11.0,
                            color=(0, 0, 0),
                        )
                    else:
                        current_page.insert_text(
                            pymupdf.Point(margin_left, current_y),
                            sline,
                            fontname=fnames["regular"],
                            fontsize=11.0,
                            color=(0, 0, 0),
                        )
                    current_y += leading_line
                current_y += 6.0

            else:
                # Custom & Accomplishments
                if entry.title:
                    if current_y + 25.0 > max_y:
                        current_page, current_y = create_page()
                    h_parts = [entry.title]
                    if entry.subtitle:
                        h_parts.append(f" - {entry.subtitle}")
                    if entry.date_range:
                        h_parts.append(f", {entry.date_range}")
                    p_head = "".join(h_parts)
                    current_page.insert_text(
                        pymupdf.Point(margin_left, current_y),
                        p_head,
                        fontname=fnames["bold"],
                        fontsize=11.0,
                        color=(0, 0, 0),
                    )
                    current_y += leading_bullet

                for b in entry.bullets:
                    if not b.enabled or not b.text.strip():
                        continue
                    if current_y + 14.0 > max_y:
                        current_page, current_y = create_page()
                    current_page.draw_circle(
                        pymupdf.Point(56.2, current_y - 3.4),
                        2.1,
                        color=(0, 0, 0),
                        fill=(0, 0, 0),
                    )
                    b_lines = split_into_lines(
                        b.text.strip(), fonts["regular"], 11.0, 495.0
                    )
                    for bl in b_lines:
                        if current_y > max_y:
                            current_page, current_y = create_page()
                        current_page.insert_text(
                            pymupdf.Point(63.0, current_y),
                            bl,
                            fontname=fnames["regular"],
                            fontsize=11.0,
                            color=(0, 0, 0),
                        )
                        current_y += leading_bullet
                current_y += 6.0

    pdf_bytes = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    return pdf_bytes


def render_resume_preview_pages(
    resume: MasterResume, dpi: int = 160, font_pt: float = 11.0
) -> dict[str, Any]:
    # Render resume to base64 PNG pages for live preview stage.
    pdf_bytes = render_resume_pdf_bytes(resume, font_pt=font_pt)
    doc = pymupdf.open("pdf", pdf_bytes)
    zoom = dpi / 72.0
    matrix = pymupdf.Matrix(zoom, zoom)
    pages: list[str] = []
    for page in doc:
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        png_data = pix.tobytes("png")
        b64 = base64.b64encode(png_data).decode("ascii")
        pages.append(f"data:image/png;base64,{b64}")
    total = len(doc)
    doc.close()
    return {"page_count": total, "pages": pages, "fits_one_page": total == 1}


def export_pdf(resume: MasterResume, output_path: str, theme: str = "gnc") -> str:
    # Export resume to PDF document file.
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    pdf_bytes = render_resume_pdf_bytes(resume)
    with open(output_path, "wb") as f:
        f.write(pdf_bytes)
    return output_path


_DOCX_BASE_PT = 10.5
_DOCX_MIN_PT = 8.0
_DOCX_LINE_FACTOR = 1.22
_DOCX_TEXT_HEIGHT_PT = 698.4
_DOCX_FIT_MARGIN = 0.975
_DOCX_CONTENT_WIDTH_PT = 504.0
_MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December",
]
_MONTH_DATE_PATTERN = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{4})\b", re.IGNORECASE
)
_NUMERIC_DATE_PATTERN = re.compile(r"\b(\d{1,2})/(\d{4})\b")
EXPORT_FORMATS: tuple[str, ...] = ("docx", "pdf", "txt")


def _convert_dates(text: str, date_format: str) -> str:
    # Rewrite month/year tokens in text to the requested date format.
    if date_format == "MM/YYYY":
        def to_numeric(match: re.Match[str]) -> str:
            month_idx = [m[:3].lower() for m in _MONTH_NAMES].index(match.group(1).lower()) + 1
            return f"{month_idx:02d}/{match.group(2)}"

        return _MONTH_DATE_PATTERN.sub(to_numeric, text)
    if date_format == "Month YYYY":
        def to_named(match: re.Match[str]) -> str:
            month_num = int(match.group(1))
            if month_num < 1 or month_num > 12:
                return match.group(0)
            return f"{_MONTH_NAMES[month_num - 1]} {match.group(2)}"

        return _NUMERIC_DATE_PATTERN.sub(to_named, text)
    return text


def apply_date_format(resume: MasterResume, date_format: str) -> MasterResume:
    # Return a copy of resume with entry date ranges rewritten to date_format.
    out = copy.deepcopy(resume)
    for sec in out.sections:
        for entry in sec.entries:
            entry.date_range = _convert_dates(entry.date_range, date_format)
    return out


def _build_docx(resume: MasterResume, body_pt: float) -> tuple[Any, float]:
    # Build the GNC-format Word document at body_pt and estimate its text height in points.
    import docx
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls

    ratio = body_pt / _DOCX_BASE_PT
    fonts = resolve_calibri_fonts()["instances"]
    doc = docx.Document()
    sec = doc.sections[0]
    sec.page_width = Inches(8.5)
    sec.page_height = Inches(11.0)
    sec.left_margin = Inches(0.75)
    sec.right_margin = Inches(0.75)
    sec.top_margin = Inches(0.65)
    sec.bottom_margin = Inches(0.65)

    style_normal = doc.styles["Normal"]
    style_normal.font.name = "Calibri"
    style_normal.font.size = Pt(body_pt)
    style_normal.paragraph_format.line_spacing = 1.0
    style_normal.paragraph_format.space_before = Pt(0)
    style_normal.paragraph_format.space_after = Pt(0)
    height = [0.0]

    def add_par(
        runs: list[tuple[str, float, bool, bool]],
        before: float = 0.0,
        after: float = 0.0,
        center: bool = False,
        right_tab: bool = False,
        bullet: bool = False,
        rule: bool = False,
    ) -> None:
        # Add one paragraph of (text, base_size, bold, italic) runs and accumulate its height.
        para = doc.add_paragraph()
        fmt = para.paragraph_format
        fmt.space_before = Pt(before * ratio)
        fmt.space_after = Pt(after * ratio)
        if center:
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if right_tab:
            fmt.tab_stops.add_tab_stop(Inches(7.0), WD_TAB_ALIGNMENT.RIGHT)
        avail = _DOCX_CONTENT_WIDTH_PT
        if bullet:
            indent = 9.0 * ratio
            fmt.left_indent = Pt(indent)
            fmt.first_line_indent = Pt(-indent)
            fmt.tab_stops.add_tab_stop(Pt(indent))
            glyph = para.add_run("\u25cf\t")
            glyph.font.name = "Arial"
            glyph.font.size = Pt(8.5 * ratio)
            avail -= indent
        total_width = 0.0
        max_size = 0.0
        for text, base_size, is_bold, is_italic in runs:
            size = base_size * ratio
            run = para.add_run(text)
            run.font.name = "Calibri"
            run.font.size = Pt(size)
            run.font.bold = is_bold
            run.font.italic = is_italic
            run.font.color.rgb = RGBColor(0, 0, 0)
            key = "bold_italic" if is_bold and is_italic else "bold" if is_bold else "italic" if is_italic else "regular"
            total_width += fonts[key].text_length(text.replace("\t", "  "), fontsize=size)
            max_size = max(max_size, size)
        if rule:
            bdr = parse_xml(
                f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="16" w:space="2" w:color="000000"/></w:pBdr>'
            )
            para._p.get_or_add_pPr().append(bdr)
            height[0] += 4.0 * ratio
        line_count = max(1, math.ceil(total_width / avail))
        height[0] += line_count * max_size * _DOCX_LINE_FACTOR + (before + after) * ratio

    def add_header(title: str) -> None:
        add_par([(title.upper(), 11.0, True, False)], before=6.0, after=2.0, rule=True)

    add_par([((resume.contact.name or "CANDIDATE NAME").upper(), 20.0, True, False)], after=2.0, center=True)
    c_parts = [
        p
        for p in [
            resume.contact.phone,
            resume.contact.email,
            resume.contact.location,
            resume.contact.linkedin,
            resume.contact.github,
            resume.contact.website,
        ]
        if p and p.strip()
    ]
    if c_parts:
        add_par([(" | ".join(c_parts), 9.5, False, False)], after=4.0, center=True)

    if resume.summary_enabled and resume.summary.strip():
        add_header("Summary")
        add_par([(resume.summary.strip(), 10.5, False, False)], after=2.0)

    for s in resume.sections:
        entries = [e for e in s.entries if e.enabled]
        if not s.enabled or not entries:
            continue
        add_header(s.title)
        stype = s.type.lower()
        for e in entries:
            date_run = [("\t" + e.date_range, 10.5, True, False)] if e.date_range else []
            if stype == "education":
                add_par([(e.title, 10.5, True, False)] + date_run, before=2.0, after=1.0, right_tab=True)
                if e.subtitle:
                    add_par([(e.subtitle, 10.5, False, True)], after=1.0)
                if e.gpa:
                    add_par([("GPA: ", 10.5, True, False), (e.gpa, 10.5, False, False)], after=1.0)
                if e.coursework:
                    add_par([("Relevant Coursework: ", 10.5, True, False), (e.coursework, 10.5, False, False)], after=2.0)
            elif stype == "skills":
                body = e.skills_text or ", ".join([b.text for b in e.bullets if b.enabled])
                add_par([(f"{e.title}: ", 10.5, True, False), (body, 10.5, False, False)], before=2.0, after=2.0)
            else:
                head_runs = [(e.title, 10.5, True, False)] if e.title else []
                if e.subtitle:
                    head_runs.append((f", {e.subtitle}", 10.5, False, True))
                add_par(head_runs + date_run, before=3.0, after=1.0, right_tab=True)
                for b in e.bullets:
                    if b.enabled and b.text.strip():
                        add_par([(b.text.strip(), 10.5, False, False)], after=1.5, bullet=True)
    return doc, height[0]


def estimate_docx_height_pt(resume: MasterResume, body_pt: float = _DOCX_BASE_PT) -> float:
    # Estimate the text height in points of the DOCX export at body_pt.
    return _build_docx(resume, body_pt)[1]


def fit_docx_font_pt(resume: MasterResume, body_pt: float = _DOCX_BASE_PT) -> float:
    # Return the largest body size at or below body_pt whose DOCX layout fits one page.
    limit = _DOCX_TEXT_HEIGHT_PT * _DOCX_FIT_MARGIN
    size = body_pt
    while size > _DOCX_MIN_PT:
        if estimate_docx_height_pt(resume, size) <= limit:
            return size
        size = round(size - 0.25, 2)
    return _DOCX_MIN_PT


def write_docx_file(resume: MasterResume, output_path: str, body_pt: float) -> str:
    # Write the DOCX export at exactly body_pt.
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    doc, _ = _build_docx(resume, body_pt)
    doc.save(output_path)
    return output_path


def export_docx(resume: MasterResume, output_path: str, theme: str = "gnc") -> str:
    # Export resume to a one-page Word DOCX matching SpaceX GNC formatting.
    return write_docx_file(resume, output_path, fit_docx_font_pt(resume))


def export_text(resume: MasterResume) -> str:
    # Export resume to plain text with uppercase section headings.
    lines: list[str] = [resume.contact.name.upper()]
    if resume.contact.title:
        lines.append(resume.contact.title)
    contact_parts = [
        p
        for p in [
            resume.contact.phone,
            resume.contact.email,
            resume.contact.location,
            resume.contact.linkedin,
            resume.contact.github,
            resume.contact.website,
        ]
        if p.strip()
    ]
    if contact_parts:
        lines.append(" | ".join(contact_parts))
    lines.append("")
    if resume.summary_enabled and resume.summary.strip():
        lines.extend(["SUMMARY", resume.summary.strip(), ""])
    for sec in resume.sections:
        entries = [e for e in sec.entries if e.enabled]
        if not sec.enabled or not entries:
            continue
        lines.append(sec.title.upper())
        for entry in entries:
            head = ", ".join([p for p in [entry.title, entry.subtitle] if p])
            if entry.date_range:
                head = f"{head} ({entry.date_range})" if head else entry.date_range
            if head:
                lines.append(head)
            if entry.gpa:
                lines.append(f"GPA: {entry.gpa}")
            if entry.coursework:
                lines.append(f"Relevant Coursework: {entry.coursework}")
            if entry.skills_text:
                lines.append(entry.skills_text)
            for b in entry.bullets:
                if b.enabled and b.text.strip():
                    lines.append(f"- {b.text.strip()}")
            lines.append("")
    return "\n".join(lines)


def export_resume_file(resume: MasterResume, output_path: str, font_pt: float = 11.0) -> dict[str, Any]:
    # Export by output extension (docx, pdf, txt) and report format, size, and page fit.
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    fmt = os.path.splitext(output_path)[1].lstrip(".").lower()
    if fmt == "docx":
        body_pt = fit_docx_font_pt(resume, max(font_pt - 0.5, _DOCX_MIN_PT))
        write_docx_file(resume, output_path, body_pt)
        fits = estimate_docx_height_pt(resume, body_pt) <= _DOCX_TEXT_HEIGHT_PT * _DOCX_FIT_MARGIN
        return {"format": fmt, "font_pt": body_pt + 0.5, "fits_one_page": fits}
    if fmt == "pdf":
        pdf_bytes = render_resume_pdf_bytes(resume, font_pt=font_pt)
        with open(output_path, "wb") as handle:
            handle.write(pdf_bytes)
        doc = pymupdf.open("pdf", pdf_bytes)
        pages = len(doc)
        doc.close()
        return {"format": fmt, "font_pt": font_pt, "fits_one_page": pages == 1}
    if fmt == "txt":
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write(export_text(resume))
        return {"format": fmt, "font_pt": font_pt, "fits_one_page": True}
    raise ValueError(f"Unsupported resume export format: .{fmt}")


def export_markdown(resume: MasterResume) -> str:
    # Export resume to clean Markdown text.
    lines: list[str] = [f"# {resume.contact.name}"]
    if resume.contact.title:
        lines.append(f"**{resume.contact.title}**")

    contact_parts = [
        p
        for p in [
            resume.contact.email,
            resume.contact.phone,
            resume.contact.location,
            resume.contact.linkedin,
            resume.contact.github,
            resume.contact.website,
        ]
        if p.strip()
    ]
    if contact_parts:
        lines.append(" | ".join(contact_parts))
    lines.append("")

    if resume.summary_enabled and resume.summary.strip():
        lines.append("## Professional Summary")
        lines.append(resume.summary.strip())
        lines.append("")

    for sec in resume.sections:
        if not sec.enabled:
            continue
        enabled_entries = [e for e in sec.entries if e.enabled]
        if not enabled_entries:
            continue

        lines.append(f"## {sec.title}")
        for entry in enabled_entries:
            sub_parts = []
            if entry.subtitle:
                sub_parts.append(f"*{entry.subtitle}*")
            if entry.location:
                sub_parts.append(entry.location)
            if entry.date_range:
                sub_parts.append(f"**{entry.date_range}**")

            header_line = f"### {entry.title}"
            if sub_parts:
                header_line += f" - {' | '.join(sub_parts)}"
            lines.append(header_line)

            if entry.gpa:
                lines.append(f"- **GPA:** {entry.gpa}")
            if entry.coursework:
                lines.append(f"- **Relevant Coursework:** {entry.coursework}")
            if entry.skills_text:
                lines.append(f"- {entry.skills_text}")

            for b in entry.bullets:
                if b.enabled and b.text.strip():
                    lines.append(f"- {b.text.strip()}")
            lines.append("")

    return "\n".join(lines)


def export_html(
    resume: MasterResume,
    theme: str = "gnc",
    layout: str = "single",
    accent_color: str = "#000000",
    palette: str = "standard",
    font_scale: float = 1.0,
) -> str:
    # Export resume to styled HTML document matching Calibri SpaceX GNC layout.
    c1 = " | ".join(
        [
            p
            for p in [
                resume.contact.phone,
                resume.contact.email,
                resume.contact.location,
            ]
            if p.strip()
        ]
    )
    c2 = " | ".join(
        [
            p
            for p in [
                resume.contact.linkedin,
                resume.contact.github,
                resume.contact.website,
            ]
            if p.strip()
        ]
    )

    html_parts = [
        "<!DOCTYPE html>",
        "<html><head><meta charset='utf-8'>",
        "<title>" + (resume.contact.name or "Resume") + "</title>",
        "<style>",
        "body { font-family: 'Calibri', 'Carlito', sans-serif; margin: 0; padding: 0.5in 0.75in; color: #000000; background: #ffffff; line-height: 1.25; font-size: 11pt; }",
        "h1 { text-align: center; font-size: 20pt; font-weight: bold; margin: 0 0 4pt 0; text-transform: uppercase; }",
        ".contact { text-align: center; font-size: 11pt; margin-bottom: 2pt; }",
        ".sec-head { font-size: 11pt; font-weight: bold; text-transform: uppercase; border-bottom: 2pt solid #000000; margin-top: 14pt; margin-bottom: 6pt; padding-bottom: 2pt; }",
        ".entry-head { display: flex; justify-content: space-between; font-weight: bold; }",
        "ul { margin: 2pt 0 6pt 0; padding-left: 0.125in; list-style-type: disc; }",
        "li { margin-bottom: 2pt; }",
        "</style></head><body>",
        f"<h1>{resume.contact.name}</h1>",
    ]
    if c1:
        html_parts.append(f"<div class='contact'>{c1}</div>")
    if c2:
        html_parts.append(f"<div class='contact'>{c2}</div>")

    for s in resume.sections:
        if not s.enabled:
            continue
        entries = [e for e in s.entries if e.enabled]
        if not entries:
            continue
        html_parts.append(f"<div class='sec-head'>{s.title}</div>")
        for e in entries:
            html_parts.append("<div class='entry'>")
            sub_title = f", <i>{e.subtitle}</i>" if e.subtitle else ""
            date_str = f"<span>{e.date_range}</span>" if e.date_range else ""
            html_parts.append(
                f"<div class='entry-head'><span><b>{e.title}</b>{sub_title}</span>{date_str}</div>"
            )
            if e.gpa:
                html_parts.append(f"<div><b>GPA:</b> {e.gpa}</div>")
            if e.coursework:
                html_parts.append(
                    f"<div><b>Relevant Coursework:</b> {e.coursework}</div>"
                )
            if e.skills_text:
                html_parts.append(f"<div>{e.skills_text}</div>")
            if e.bullets:
                html_parts.append("<ul>")
                for b in e.bullets:
                    if b.enabled and b.text.strip():
                        html_parts.append(f"<li>{b.text.strip()}</li>")
                html_parts.append("</ul>")
            html_parts.append("</div>")

    html_parts.append("</body></html>")
    return "".join(html_parts)
