"""Master Resume data structures, tailoring engine, ATS keyword matcher, and exporters."""
from __future__ import annotations

import json
import os
import re
import uuid
import zipfile
from dataclasses import dataclass, field, asdict
from typing import Any
import xml.etree.ElementTree as ET
import pymupdf


@dataclass
class BulletPoint:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    text: str = ""
    enabled: bool = True


@dataclass
class ResumeEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""        # e.g., Senior Software Engineer / B.S. Computer Science / Cloud Migration Project
    subtitle: str = ""     # e.g., Stripe / Stanford University / Open Source
    date_range: str = ""   # e.g., 2022 - Present / 2018 - 2022
    location: str = ""     # e.g., San Francisco, CA / Remote
    bullets: list[BulletPoint] = field(default_factory=list)
    enabled: bool = True


@dataclass
class ResumeSection:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: str = "experience"  # "experience", "projects", "skills", "education", "custom"
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
    summary_enabled: bool = True
    sections: list[ResumeSection] = field(default_factory=list)
    profiles: dict[str, dict[str, Any]] = field(default_factory=dict)


def create_sample_master_resume() -> MasterResume:
    """Create a rich, comprehensive sample master resume."""
    contact = ContactInfo(
        name="Alex Morgan",
        title="Lead Software Engineer & Solutions Architect",
        email="alex.morgan@example.com",
        phone="(555) 019-2834",
        location="San Francisco, CA (Open to Remote)",
        linkedin="linkedin.com/in/alexmorgan",
        github="github.com/alexmorgan",
        website="alexmorgan.dev",
    )
    summary = (
        "High-impact software engineering leader with 8+ years architecting scalable cloud-native platforms, "
        "distributed systems, and developer tooling. Proven track record driving 40% performance gains and leading "
        "cross-functional engineering squads."
    )

    # Section 1: Experience
    exp = ResumeSection(id="sec_exp", type="experience", title="Professional Experience", enabled=True)

    e1 = ResumeEntry(
        id="exp_1",
        title="Senior Staff Software Engineer",
        subtitle="Stripe / Fintech Corp",
        date_range="2022 - Present",
        location="San Francisco, CA",
        enabled=True,
        bullets=[
            BulletPoint(id="b1", text="Architected ultra-low-latency payment processing pipeline handling $4B+ annualized volume with 99.999% uptime.", enabled=True),
            BulletPoint(id="b3", text="Mentored 12 engineers across backend and infrastructure teams; spearheaded company-wide zero-downtime deployment standard.", enabled=True),
            BulletPoint(id="b4", text="Designed distributed transaction ledger with PostgreSQL and Redis caching, preventing $1.2M in potential race conditions.", enabled=True),
            BulletPoint(id="b5", text="Reduced AWS cloud spend by $320k/year through automated spot instance scheduling and auto-scaling optimizations.", enabled=False),
        ]
    )

    e2 = ResumeEntry(
        id="exp_2",
        title="Software Engineer II",
        subtitle="Datadog / Cloud Scale Inc",
        date_range="2019 - 2022",
        location="New York, NY",
        enabled=True,
        bullets=[
            BulletPoint(id="b6", text="Engineered real-time telemetry indexing pipeline in Python and C++ ingesting 250k events/second.", enabled=True),
            BulletPoint(id="b7", text="Built automated anomaly detection service using scikit-learn that reduced false-positive alerts by 60%.", enabled=True),
            BulletPoint(id="b8", text="Authored comprehensive internal developer SDKs downloaded 100k+ times by 80+ engineering teams.", enabled=True),
        ]
    )
    exp.entries = [e1, e2]

    # Section 2: Projects
    proj = ResumeSection(id="sec_proj", type="projects", title="Featured Projects", enabled=True)
    p1 = ResumeEntry(
        id="proj_1",
        title="FOSSEverything - Local-First Desktop Utilities",
        subtitle="Creator & Lead Maintainer",
        date_range="2024",
        location="github.com/FOSSEverything",
        enabled=True,
        bullets=[
            BulletPoint(id="b9", text="Built 100% offline desktop productivity suite with PyMuPDF, FFmpeg, and OCR engines.", enabled=True),
            BulletPoint(id="b10", text="Engineered zero-cloud document rendering, video/audio transcoding, and structured data querying.", enabled=True),
        ]
    )
    proj.entries = [p1]

    # Section 3: Skills
    skills = ResumeSection(id="sec_skills", type="skills", title="Technical Skills", enabled=True)
    s1 = ResumeEntry(
        id="skill_1",
        title="Languages & Technologies",
        subtitle="Python, Go, TypeScript, Rust, C++, FastAPI, gRPC, React",
        date_range="",
        location="",
        enabled=True,
        bullets=[
            BulletPoint(id="b11", text="Backend: Python (FastAPI, Django), Go, Rust, Node.js, gRPC, REST APIs", enabled=True),
            BulletPoint(id="b12", text="Cloud & DevOps: AWS (ECS, EKS, Lambda, S3, RDS), Kubernetes, Docker, Terraform, CI/CD", enabled=True),
            BulletPoint(id="b13", text="Databases: PostgreSQL, Redis, DynamoDB, MongoDB, Elasticsearch, Kafka", enabled=True),
            BulletPoint(id="b14", text="Frontend & Mobile: TypeScript, React, Next.js, Tailwind CSS, PyQt6 / Desktop GUI", enabled=False),
        ]
    )
    skills.entries = [s1]

    # Section 4: Education
    edu = ResumeSection(id="sec_edu", type="education", title="Education", enabled=True)
    ed1 = ResumeEntry(
        id="edu_1",
        title="B.S. in Computer Science & Mathematics",
        subtitle="University of California, Berkeley",
        date_range="2015 - 2019",
        location="Berkeley, CA",
        enabled=True,
        bullets=[
            BulletPoint(id="b15", text="Honors: Magna Cum Laude, Dean's Honors List (all semesters).", enabled=True),
            BulletPoint(id="b16", text="Coursework: Distributed Systems, Operating Systems, Algorithms & Complexity, Database Systems.", enabled=True),
        ]
    )
    edu.entries = [ed1]

    resume = MasterResume(
        contact=contact,
        summary=summary,
        summary_enabled=True,
        sections=[exp, proj, skills, edu],
        profiles={
            "Backend Lead": {
                "summary": True,
                "sections": {"sec_exp": True, "sec_proj": True, "sec_skills": True, "sec_edu": True},
                "entries": {"exp_1": True, "exp_2": True, "proj_1": True, "skill_1": True, "edu_1": True},
                "bullets": {"b1": True, "b2": True, "b3": True, "b4": True, "b5": False, "b6": True, "b7": True, "b8": True, "b9": True, "b10": True, "b11": True, "b12": True, "b13": True, "b14": False, "b15": True, "b16": True}
            }
        }
    )
    return resume


# ─── Serialization & Persistence ─────────────────────────────────────────────────────
def resume_to_dict(resume: MasterResume) -> dict[str, Any]:
    return asdict(resume)


def resume_from_dict(d: dict[str, Any]) -> MasterResume:
    contact_d = d.get("contact", {})
    contact = ContactInfo(**contact_d) if isinstance(contact_d, dict) else ContactInfo()

    sections = []
    for s in d.get("sections", []):
        entries = []
        for e in s.get("entries", []):
            bullets = [BulletPoint(**b) if isinstance(b, dict) else b for b in e.get("bullets", [])]
            entries.append(ResumeEntry(
                id=e.get("id", ""),
                title=e.get("title", ""),
                subtitle=e.get("subtitle", ""),
                date_range=e.get("date_range", ""),
                location=e.get("location", ""),
                bullets=bullets,
                enabled=e.get("enabled", True),
            ))
        sections.append(ResumeSection(
            id=s.get("id", ""),
            type=s.get("type", "custom"),
            title=s.get("title", "Section"),
            entries=entries,
            enabled=s.get("enabled", True),
        ))

    return MasterResume(
        contact=contact,
        summary=d.get("summary", ""),
        summary_enabled=d.get("summary_enabled", True),
        sections=sections,
        profiles=d.get("profiles", {}),
    )


def save_resume_file(resume: MasterResume, path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(resume_to_dict(resume), f, indent=2)


def load_resume_file(path: str) -> MasterResume:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return resume_from_dict(data)


# ─── ATS Keyword Matcher ────────────────────────────────────────────────────────────
COMMON_STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't",
    "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have",
    "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him",
    "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't",
    "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor",
    "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out",
    "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some",
    "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there",
    "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those", "through",
    "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've",
    "were", "weren't", "what", "what's", "when", "when's", "where", "where's", "which", "while", "who",
    "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're",
    "you've", "your", "yours", "yourself", "yourselves", "will", "experience", "work", "years", "team", "role",
    "job", "candidate", "responsibilities", "requirements", "plus", "must", "required", "preferred"
}


def extract_keywords(text: str) -> list[str]:
    """Tokenize and extract candidate keywords from job description or resume."""
    tokens = re.findall(r"[a-zA-Z0-9+#.-]+", text.lower())
    cleaned = []
    for t in tokens:
        t_clean = t.strip(".,;:()")
        if len(t_clean) >= 2 and t_clean not in COMMON_STOPWORDS and not t_clean.isdigit():
            cleaned.append(t_clean)
    return cleaned


def analyze_ats_match(resume: MasterResume, job_description: str) -> dict[str, Any]:
    """Compute keyword match percentage and identify missing key terms."""
    if not job_description.strip():
        return {"score": 0, "matched": [], "missing": [], "total_keywords": 0}

    resume_text_parts = [resume.contact.title]
    if resume.summary_enabled:
        resume_text_parts.append(resume.summary)

    for sec in resume.sections:
        if not sec.enabled:
            continue
        resume_text_parts.append(sec.title)
        for entry in sec.entries:
            if not entry.enabled:
                continue
            resume_text_parts.extend([entry.title, entry.subtitle, entry.location])
            for b in entry.bullets:
                if b.enabled:
                    resume_text_parts.append(b.text)

    resume_corpus = " ".join(resume_text_parts).lower()

    job_tokens = extract_keywords(job_description)
    freq: dict[str, int] = {}
    for tok in job_tokens:
        freq[tok] = freq.get(tok, 0) + 1

    sorted_keywords = sorted(freq.items(), key=lambda kv: -kv[1])

    matched = []
    missing = []
    for kw, count in sorted_keywords[:50]:
        if kw in resume_corpus:
            matched.append((kw, count))
        else:
            missing.append((kw, count))

    total = len(matched) + len(missing)
    score = int((len(matched) / total * 100)) if total > 0 else 0

    return {
        "score": score,
        "matched": matched,
        "missing": missing,
        "total_keywords": total,
    }


# ─── Resume Layout & Versioning ───────────────────────────────────────────────────
def _snapshot_profile_state(resume: MasterResume) -> dict[str, Any]:
    """Capture the current enabled/disabled state of a profile into a stable dict."""
    state = {
        "summary": resume.summary_enabled,
        "sections": {},
        "entries": {},
        "bullets": {},
    }
    for sec in resume.sections:
        state["sections"][sec.id] = sec.enabled
        for entry in sec.entries:
            state["entries"][entry.id] = entry.enabled
            for bullet in entry.bullets:
                state["bullets"][bullet.id] = bullet.enabled
    return state


def capture_profile_version(resume: MasterResume, profile_name: str, note: str = "") -> dict[str, Any] | None:
    """Store a snapshot of a saved profile so users can compare successive tailoring changes."""
    if profile_name not in resume.profiles:
        return None
    profile = resume.profiles[profile_name]
    history = profile.setdefault("history", [])
    snapshot = {
        "note": note or f"Version {len(history) + 1}",
        "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "state": _snapshot_profile_state(resume),
    }
    history.append(snapshot)
    return snapshot


def diff_profile_versions(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Compare two saved profile snapshots and summarize what changed."""
    changed = {"summary": before.get("summary") != after.get("summary")}
    sections = []
    entries = []
    bullets = []

    before_sections = before.get("sections", {})
    after_sections = after.get("sections", {})
    for sec_id in sorted(set(before_sections) | set(after_sections)):
        if before_sections.get(sec_id) != after_sections.get(sec_id):
            sections.append({"id": sec_id, "before": before_sections.get(sec_id), "after": after_sections.get(sec_id)})

    before_entries = before.get("entries", {})
    after_entries = after.get("entries", {})
    for entry_id in sorted(set(before_entries) | set(after_entries)):
        if before_entries.get(entry_id) != after_entries.get(entry_id):
            entries.append({"id": entry_id, "before": before_entries.get(entry_id), "after": after_entries.get(entry_id)})

    before_bullets = before.get("bullets", {})
    after_bullets = after.get("bullets", {})
    for bullet_id in sorted(set(before_bullets) | set(after_bullets)):
        if before_bullets.get(bullet_id) != after_bullets.get(bullet_id):
            bullets.append({"id": bullet_id, "before": before_bullets.get(bullet_id), "after": after_bullets.get(bullet_id)})

    changed["sections"] = sections
    changed["entries"] = entries
    changed["bullets"] = bullets
    return changed


def export_html(resume: MasterResume, theme: str = "modern", layout: str = "single", accent_color: str | None = None, palette: dict[str, str] | None = None, font_scale: float = 1.0) -> str:
    """Export the tailored resume as a minimal HTML document with optional dual-column layout styling."""
    safe_theme = (theme or "modern").lower()
    scale = max(0.75, float(font_scale) if isinstance(font_scale, (int, float)) else 1.0)
    # noqa: 28 (exported resume document's own color theme, independent of the app UI theme module)
    resolved_palette = {
        "page_bg": "#0f172a" if safe_theme.startswith("dark") else "#f3f4f6",  # noqa: 28
        "surface": "#111827" if safe_theme.startswith("dark") else "#ffffff",  # noqa: 28
        "surface_alt": "#1f2937" if safe_theme.startswith("dark") else "#f8fafc",  # noqa: 28
        "text": "#f8fafc" if safe_theme.startswith("dark") else "#111827",  # noqa: 28
        "muted": "#cbd5e1" if safe_theme.startswith("dark") else "#4b5563",  # noqa: 28
        "border": "#334155" if safe_theme.startswith("dark") else "#dbe4f0",  # noqa: 28
        "shadow": "rgba(15, 23, 42, 0.28)" if safe_theme.startswith("dark") else "rgba(15, 23, 42, 0.08)",
        "accent": "#2563eb",  # noqa: 28
    }
    if isinstance(palette, dict):
        resolved_palette.update({key: value for key, value in palette.items() if isinstance(value, str) and value.strip()})
    accent = accent_color or resolved_palette.get("accent") or "currentColor"
    base_font = max(12.0, 16.0 * scale)
    small_font = max(11.0, base_font * 0.8)
    label_font = max(12.0, base_font * 0.82)
    heading_font = max(28.0, base_font * 1.8)
    if layout == "dual-column":
        css = f"""
        :root {{
            --page-bg: {resolved_palette['page_bg']};
            --surface: {resolved_palette['surface']};
            --surface-alt: {resolved_palette['surface_alt']};
            --text: {resolved_palette['text']};
            --muted: {resolved_palette['muted']};
            --border: {resolved_palette['border']};
            --shadow: {resolved_palette['shadow']};
            --accent: {accent};
            --base-font: {base_font:.2f}px;
            --small-font: {small_font:.2f}px;
            --label-font: {label_font:.2f}px;
            --heading-font: {heading_font:.2f}px;
        }}
        body {{ font-family: Arial, sans-serif; margin: 0; background: var(--page-bg); color: var(--text); font-size: var(--base-font); }}
        .resume-page {{ max-width: 1100px; margin: 24px auto; background: var(--surface); padding: 28px; box-shadow: 0 1px 3px var(--shadow); }}
        .resume-layout {{ display: grid; grid-template-columns: 300px 1fr; gap: 32px; }}
        .sidebar {{ background: var(--surface-alt); border-right: 2px solid var(--accent); padding-right: 20px; }}
        .main {{ padding-left: 8px; }}
        .name {{ font-size: var(--heading-font); font-weight: 700; color: var(--text); margin: 0; }}
        .title {{ color: var(--accent); font-weight: 700; margin-top: 4px; }}
        .meta {{ font-size: var(--small-font); color: var(--muted); margin-top: 10px; line-height: 1.5; }}
        .section-title {{ font-size: var(--label-font); letter-spacing: 0.08em; text-transform: uppercase; color: var(--accent); font-weight: 700; border-bottom: 1px solid var(--border); padding-bottom: 4px; margin: 16px 0 10px; }}
        .entry-title {{ font-size: var(--base-font); font-weight: 700; color: var(--text); }}
        .entry-meta {{ font-size: var(--small-font); color: var(--muted); margin: 3px 0; }}
        ul {{ margin: 6px 0 0 0; padding-left: 18px; }}
        li {{ margin-bottom: 6px; }}
        """
    else:
        css = f"""
        :root {{
            --page-bg: {resolved_palette['page_bg']};
            --surface: {resolved_palette['surface']};
            --surface-alt: {resolved_palette['surface_alt']};
            --text: {resolved_palette['text']};
            --muted: {resolved_palette['muted']};
            --border: {resolved_palette['border']};
            --shadow: {resolved_palette['shadow']};
            --accent: {accent};
            --base-font: {base_font:.2f}px;
            --small-font: {small_font:.2f}px;
            --label-font: {label_font:.2f}px;
            --heading-font: {heading_font:.2f}px;
        }}
        body {{ font-family: Arial, sans-serif; margin: 0; background: var(--page-bg); color: var(--text); font-size: var(--base-font); }}
        .resume-page {{ max-width: 850px; margin: 24px auto; background: var(--surface); padding: 30px; box-shadow: 0 1px 3px var(--shadow); }}
        .name {{ font-size: var(--heading-font); font-weight: 700; margin: 0; color: var(--text); }}
        .title {{ color: var(--accent); font-weight: 700; margin-top: 4px; }}
        .meta {{ font-size: var(--small-font); color: var(--muted); margin-top: 10px; }}
        .section-title {{ font-size: var(--label-font); text-transform: uppercase; letter-spacing: 0.08em; color: var(--accent); font-weight: 700; border-bottom: 1px solid var(--border); padding-bottom: 4px; margin: 16px 0 10px; }}
        .entry-title {{ font-size: var(--base-font); font-weight: 700; color: var(--text); }}
        .entry-meta {{ font-size: var(--small-font); color: var(--muted); margin: 3px 0; }}
        ul {{ margin: 6px 0 0 0; padding-left: 18px; }}
        li {{ margin-bottom: 6px; }}
        """

    lines = [
        "<!DOCTYPE html>",
        "<html><head><meta charset='utf-8'><style>" + css + "</style></head><body>",
        "<div class='resume-page'>",
    ]

    if layout == "dual-column":
        lines.append("<div class='resume-layout'><aside class='sidebar'>")
    else:
        lines.append("<div>")

    lines.append(f"<h1 class='name'>{resume.contact.name}</h1>")
    if resume.contact.title:
        lines.append(f"<div class='title'>{resume.contact.title}</div>")
    contact_parts = []
    if resume.contact.email: contact_parts.append(resume.contact.email)
    if resume.contact.phone: contact_parts.append(resume.contact.phone)
    if resume.contact.location: contact_parts.append(resume.contact.location)
    if resume.contact.linkedin: contact_parts.append(f"<a href='https://{resume.contact.linkedin}'>{resume.contact.linkedin}</a>")
    if resume.contact.github: contact_parts.append(f"<a href='https://{resume.contact.github}'>{resume.contact.github}</a>")
    if resume.contact.website: contact_parts.append(f"<a href='https://{resume.contact.website}'>{resume.contact.website}</a>")
    if contact_parts:
        lines.append("<div class='meta'>" + " | ".join(contact_parts) + "</div>")

    if resume.summary_enabled and resume.summary.strip():
        lines.append("<div class='section-title'>Professional Summary</div>")
        lines.append(f"<div>{resume.summary.strip()}</div>")

    if layout == "dual-column":
        lines.append("</aside><main class='main'>")

    for sec in resume.sections:
        if not sec.enabled:
            continue
        enabled_entries = [entry for entry in sec.entries if entry.enabled]
        if not enabled_entries:
            continue
        lines.append(f"<div class='section-title'>{sec.title}</div>")
        for entry in enabled_entries:
            line = f"<div class='entry-title'>{entry.title}</div>"
            meta_parts = []
            if entry.subtitle: meta_parts.append(entry.subtitle)
            if entry.location: meta_parts.append(entry.location)
            if entry.date_range: meta_parts.append(entry.date_range)
            if meta_parts:
                line += f"<div class='entry-meta'>{' | '.join(meta_parts)}</div>"
            lines.append(line)
            if entry.bullets:
                lines.append("<ul>")
                for bullet in entry.bullets:
                    if bullet.enabled and bullet.text.strip():
                        lines.append(f"<li>{bullet.text.strip()}</li>")
                lines.append("</ul>")

    if layout == "dual-column":
        lines.append("</main></div>")
    else:
        lines.append("</div>")
    lines.extend(["</div>", "</body></html>"])
    return "\n".join(lines)


def save_profile(resume: MasterResume, profile_name: str) -> None:
    """Capture current enabled/disabled state of all sections, entries, and bullets."""
    state = _snapshot_profile_state(resume)
    if profile_name in resume.profiles and isinstance(resume.profiles[profile_name], dict):
        history = resume.profiles[profile_name].setdefault("history", [])
        state["history"] = history
    resume.profiles[profile_name] = state


def apply_profile(resume: MasterResume, profile_name: str) -> bool:
    """Apply saved profile states onto the resume."""
    if profile_name not in resume.profiles:
        return False
    state = resume.profiles[profile_name]
    if "history" in state:
        state = {k: v for k, v in state.items() if k != "history"}
    resume.summary_enabled = state.get("summary", True)

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


# ─── Exporters: Markdown, HTML, PDF ───────────────────────────────────────────────
def export_docx(resume: MasterResume, output_path: str, theme: str = "modern") -> str:
    """Export the current resume configuration as a minimal DOCX file."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)

    def xml_text(value: str) -> str:
        return (value or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    paragraphs = []
    paragraphs.append(f'<w:p><w:r><w:t>{xml_text(resume.contact.name)}</w:t></w:r></w:p>')
    if resume.contact.title:
        paragraphs.append(f'<w:p><w:r><w:t>{xml_text(resume.contact.title)}</w:t></w:r></w:p>')

    contact_parts = []
    if resume.contact.email: contact_parts.append(resume.contact.email)
    if resume.contact.phone: contact_parts.append(resume.contact.phone)
    if resume.contact.location: contact_parts.append(resume.contact.location)
    if resume.contact.linkedin: contact_parts.append(resume.contact.linkedin)
    if resume.contact.github: contact_parts.append(resume.contact.github)
    if resume.contact.website: contact_parts.append(resume.contact.website)
    if contact_parts:
        paragraphs.append(f'<w:p><w:r><w:t>{xml_text(" | ".join(contact_parts))}</w:t></w:r></w:p>')

    if resume.summary_enabled and resume.summary.strip():
        paragraphs.append(f'<w:p><w:r><w:t>{xml_text("Professional Summary")}</w:t></w:r></w:p>')
        paragraphs.append(f'<w:p><w:r><w:t>{xml_text(resume.summary.strip())}</w:t></w:r></w:p>')

    for sec in resume.sections:
        if not sec.enabled:
            continue
        enabled_entries = [entry for entry in sec.entries if entry.enabled]
        if not enabled_entries:
            continue
        paragraphs.append(f'<w:p><w:r><w:t>{xml_text(sec.title)}</w:t></w:r></w:p>')
        for entry in enabled_entries:
            parts = []
            if entry.subtitle: parts.append(entry.subtitle)
            if entry.location: parts.append(entry.location)
            if entry.date_range: parts.append(entry.date_range)
            heading = entry.title if not parts else f"{entry.title} - {' | '.join(parts)}"
            paragraphs.append(f'<w:p><w:r><w:t>{xml_text(heading)}</w:t></w:r></w:p>')
            for bullet in entry.bullets:
                if bullet.enabled and bullet.text.strip():
                    paragraphs.append(f'<w:p><w:r><w:t>{xml_text(f"- {bullet.text.strip()}")}</w:t></w:r></w:p>')

    document_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:w10="urn:schemas-microsoft-com:office:word" xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml" xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk" xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml" xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" mc:Ignorable="w14 w15 wp14">
  <w:body>
    {"".join(paragraphs)}
    <w:sectPr>
      <w:pgSz w:w="12240" w:h="15840"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>
'''

    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
'''

    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
'''

    core_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{xml_text(resume.contact.name)}</dc:title>
  <dc:creator>{xml_text(resume.contact.name)}</dc:creator>
  <cp:lastModifiedBy>{xml_text(resume.contact.name)}</cp:lastModifiedBy>
</cp:coreProperties>
'''

    app_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>FOSSEverything</Application>
</Properties>
'''

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("docProps/core.xml", core_xml)
        zf.writestr("docProps/app.xml", app_xml)
        zf.writestr("word/document.xml", document_xml)
    return output_path


def export_markdown(resume: MasterResume) -> str:
    lines = []
    lines.append(f"# {resume.contact.name}")
    if resume.contact.title:
        lines.append(f"**{resume.contact.title}**")

    contact_parts = []
    if resume.contact.email: contact_parts.append(resume.contact.email)
    if resume.contact.phone: contact_parts.append(resume.contact.phone)
    if resume.contact.location: contact_parts.append(resume.contact.location)
    if resume.contact.linkedin: contact_parts.append(resume.contact.linkedin)
    if resume.contact.github: contact_parts.append(resume.contact.github)
    if resume.contact.website: contact_parts.append(resume.contact.website)
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
            if entry.subtitle: sub_parts.append(f"*{entry.subtitle}*")
            if entry.location: sub_parts.append(entry.location)
            if entry.date_range: sub_parts.append(f"**{entry.date_range}**")

            header_line = f"### {entry.title}"
            if sub_parts:
                header_line += f" - {' | '.join(sub_parts)}"
            lines.append(header_line)

            for b in entry.bullets:
                if b.enabled and b.text.strip():
                    lines.append(f"- {b.text.strip()}")
            lines.append("")

    return "\n".join(lines)


def export_pdf(resume: MasterResume, output_path: str, theme: str = "modern") -> str:
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    doc = pymupdf.open()

    page_width, page_height = 612, 792
    margin_x = 40
    margin_top = 40
    margin_bottom = 40
    content_width = page_width - (margin_x * 2)

    page = doc.new_page(width=page_width, height=page_height)
    y = margin_top

    def check_page_break(needed_height: float) -> None:
        nonlocal page, y
        if y + needed_height > (page_height - margin_bottom):
            page = doc.new_page(width=page_width, height=page_height)
            y = margin_top

    c_primary = (0.1, 0.2, 0.5) if theme == "modern" else (0.1, 0.1, 0.1)
    c_text = (0.15, 0.15, 0.15)
    c_gray = (0.35, 0.35, 0.35)

    c = resume.contact
    if c.name:
        page.insert_text((margin_x, y + 18), c.name, fontsize=20, fontname="helv", color=c_primary)
        y += 26

    if c.title:
        page.insert_text((margin_x, y + 11), c.title, fontsize=11, fontname="helv", color=c_primary)
        y += 16

    contact_parts = []
    if c.email: contact_parts.append(c.email)
    if c.phone: contact_parts.append(c.phone)
    if c.location: contact_parts.append(c.location)
    if c.linkedin: contact_parts.append(c.linkedin)
    if c.github: contact_parts.append(c.github)
    if c.website: contact_parts.append(c.website)

    if contact_parts:
        contact_str = " - ".join(contact_parts)
        page.insert_text((margin_x, y + 9), contact_str, fontsize=8.5, fontname="helv", color=c_gray)
        y += 14

    page.draw_line((margin_x, y), (margin_x + content_width, y), color=c_primary, width=1.5)
    y += 12

    if resume.summary_enabled and resume.summary.strip():
        check_page_break(40)
        page.insert_text((margin_x, y + 10), "PROFESSIONAL SUMMARY", fontsize=10, fontname="helv", color=c_primary)
        y += 14
        rect = pymupdf.Rect(margin_x, y, margin_x + content_width, y + 45)
        page.insert_textbox(rect, resume.summary.strip(), fontsize=9, fontname="helv", color=c_text)
        y += 36

    for sec in resume.sections:
        if not sec.enabled:
            continue
        enabled_entries = [e for e in sec.entries if e.enabled]
        if not enabled_entries:
            continue

        check_page_break(30)
        page.insert_text((margin_x, y + 10), sec.title.upper(), fontsize=10, fontname="helv", color=c_primary)
        page.draw_line((margin_x, y + 13), (margin_x + content_width, y + 13), color=(0.8, 0.8, 0.8), width=0.75)
        y += 18

        for entry in enabled_entries:
            check_page_break(25)
            page.insert_text((margin_x, y + 9), entry.title, fontsize=9.5, fontname="helv", color=c_text)
            if entry.date_range:
                date_w = pymupdf.get_text_length(entry.date_range, fontname="helv", fontsize=8.5)
                page.insert_text((margin_x + content_width - date_w, y + 9), entry.date_range, fontsize=8.5, fontname="helv", color=c_gray)
            y += 12

            if entry.subtitle or entry.location:
                sub_text = entry.subtitle
                if entry.subtitle and entry.location:
                    sub_text += f" - {entry.location}"
                elif entry.location:
                    sub_text = entry.location
                page.insert_text((margin_x, y + 8), sub_text, fontsize=8.5, fontname="helv", color=c_gray)
                y += 12

            active_bullets = [b for b in entry.bullets if b.enabled and b.text.strip()]
            for b in active_bullets:
                check_page_break(18)
                page.insert_text((margin_x + 4, y + 8), "-", fontsize=8, fontname="helv", color=c_primary)
                rect = pymupdf.Rect(margin_x + 14, y, margin_x + content_width, y + 30)
                page.insert_textbox(rect, b.text.strip(), fontsize=8.5, fontname="helv", color=c_text)
                y += 13

            y += 4

        y += 6

    doc.save(output_path)
    doc.close()
    return output_path
