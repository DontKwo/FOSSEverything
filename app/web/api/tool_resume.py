from typing import Any

from app.features.resume.ops import (
    BulletPoint,
    ContactInfo,
    MasterResume,
    ResumeEntry,
    ResumeSection,
    analyze_ats_match,
    apply_profile,
    create_sample_master_resume,
    export_docx,
    export_html,
    export_markdown,
    export_pdf,
    load_resume_file,
    resume_from_dict,
    resume_to_dict,
    save_profile,
    save_resume_file,
)
from app.web.api.result import api_method, ok, require


class ResumeApiMixin:
    @api_method
    def resume_sample(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return populated sample master resume data model.
        sample = create_sample_master_resume()
        return ok(resume=resume_to_dict(sample))

    @api_method
    def resume_load_file(self, params: dict[str, Any]) -> dict[str, Any]:
        # Load master resume JSON file from disk.
        require(params, "file_path")
        file_path = str(params["file_path"])
        res_obj = load_resume_file(file_path)
        return ok(resume=resume_to_dict(res_obj), file_path=file_path)

    @api_method
    def resume_save_file(self, params: dict[str, Any]) -> dict[str, Any]:
        # Save master resume data structure to disk.
        require(params, "resume", "output_path")
        out_p = str(params["output_path"])
        res_obj = resume_from_dict(dict(params["resume"]))
        save_resume_file(res_obj, out_p)
        return ok(output_path=out_p)

    @api_method
    def resume_render_html(self, params: dict[str, Any]) -> dict[str, Any]:
        # Render HTML document preview for resume profile.
        require(params, "resume")
        res_obj = resume_from_dict(dict(params["resume"]))
        profile = params.get("profile")
        if profile:
            active_obj = apply_profile(res_obj, str(profile))
        else:
            active_obj = res_obj
        layout = str(params.get("layout", "single"))
        accent = str(params.get("accent_color", "#2563eb"))
        html_out = export_html(active_obj, layout=layout, accent_color=accent)
        return ok(html=html_out)

    @api_method
    def resume_export_markdown(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export resume content as structured Markdown.
        require(params, "resume")
        res_obj = resume_from_dict(dict(params["resume"]))
        profile = params.get("profile")
        if profile:
            res_obj = apply_profile(res_obj, str(profile))
        md_text = export_markdown(res_obj)
        out_p = params.get("output_path")
        if out_p:
            from pathlib import Path
            Path(str(out_p)).write_text(md_text, encoding="utf-8")
        return ok(markdown=md_text, output_path=out_p)

    @api_method
    def resume_export_pdf(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export resume profile to formatted PDF document.
        require(params, "resume", "output_path")
        out_p = str(params["output_path"])
        res_obj = resume_from_dict(dict(params["resume"]))
        profile = params.get("profile")
        if profile:
            res_obj = apply_profile(res_obj, str(profile))
        layout = str(params.get("layout", "single"))
        accent = str(params.get("accent_color", "#2563eb"))
        export_pdf(res_obj, out_p, layout=layout, accent_color=accent)
        return ok(output_path=out_p)

    @api_method
    def resume_export_docx(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export resume profile to Word DOCX document.
        require(params, "resume", "output_path")
        out_p = str(params["output_path"])
        res_obj = resume_from_dict(dict(params["resume"]))
        profile = params.get("profile")
        if profile:
            res_obj = apply_profile(res_obj, str(profile))
        export_docx(res_obj, out_p)
        return ok(output_path=out_p)

    @api_method
    def resume_analyze_ats(self, params: dict[str, Any]) -> dict[str, Any]:
        # Analyze keyword matching score against job description.
        require(params, "resume", "job_description")
        res_obj = resume_from_dict(dict(params["resume"]))
        job_desc = str(params["job_description"])
        score, matched, missing = analyze_ats_match(res_obj, job_desc)
        return ok(score=round(score, 1), matched_keywords=matched, missing_keywords=missing)

    @api_method
    def resume_save_profile(self, params: dict[str, Any]) -> dict[str, Any]:
        # Save tailored profile configuration inside master resume.
        require(params, "resume", "profile_name", "selection")
        res_obj = resume_from_dict(dict(params["resume"]))
        save_profile(res_obj, str(params["profile_name"]), dict(params["selection"]))
        return ok(resume=resume_to_dict(res_obj))

    @api_method
    def resume_apply_profile(self, params: dict[str, Any]) -> dict[str, Any]:
        # Apply profile filter to master resume.
        require(params, "resume", "profile_name")
        res_obj = resume_from_dict(dict(params["resume"]))
        filtered = apply_profile(res_obj, str(params["profile_name"]))
        return ok(resume=resume_to_dict(filtered))
