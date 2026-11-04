from typing import Any

from app.features.resume.ops import (
    MasterResume,
    analyze_ats_match,
    apply_profile,
    create_sample_master_resume,
    export_docx,
    export_html,
    export_markdown,
    export_pdf,
    load_resume_file,
    render_resume_preview_pages,
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
        raw_resume = params["resume"]
        res_obj = resume_from_dict(raw_resume if isinstance(raw_resume, MasterResume) else dict(raw_resume))
        save_resume_file(res_obj, out_p)
        return ok(output_path=out_p)

    @api_method
    def resume_render_preview(self, params: dict[str, Any]) -> dict[str, Any]:
        # Render high-DPI live preview pages for resume profile.
        require(params, "resume")
        raw_resume = params["resume"]
        res_obj = resume_from_dict(raw_resume if isinstance(raw_resume, MasterResume) else dict(raw_resume))
        profile = params.get("profile")
        if profile:
            apply_profile(res_obj, str(profile))
        font_pt = float(params.get("font_pt", 11.0))
        dpi = int(params.get("dpi", 160))
        preview_data = render_resume_preview_pages(res_obj, dpi=dpi, font_pt=font_pt)
        return ok(**preview_data)

    @api_method
    def resume_render_html(self, params: dict[str, Any]) -> dict[str, Any]:
        # Render HTML document preview for resume profile.
        require(params, "resume")
        raw_resume = params["resume"]
        res_obj = resume_from_dict(raw_resume if isinstance(raw_resume, MasterResume) else dict(raw_resume))
        profile = params.get("profile")
        if profile:
            apply_profile(res_obj, str(profile))
        layout = str(params.get("layout", "single"))
        accent = str(params.get("accent_color", "#000000"))
        html_out = export_html(res_obj, layout=layout, accent_color=accent)
        return ok(html=html_out)

    @api_method
    def resume_export_markdown(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export resume content as structured Markdown.
        require(params, "resume")
        raw_resume = params["resume"]
        res_obj = resume_from_dict(raw_resume if isinstance(raw_resume, MasterResume) else dict(raw_resume))
        profile = params.get("profile")
        if profile:
            apply_profile(res_obj, str(profile))
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
        raw_resume = params["resume"]
        res_obj = resume_from_dict(raw_resume if isinstance(raw_resume, MasterResume) else dict(raw_resume))
        profile = params.get("profile")
        if profile:
            apply_profile(res_obj, str(profile))
        export_pdf(res_obj, out_p)
        return ok(output_path=out_p)

    @api_method
    def resume_export_docx(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export resume profile to Word DOCX document.
        require(params, "resume", "output_path")
        out_p = str(params["output_path"])
        raw_resume = params["resume"]
        res_obj = resume_from_dict(raw_resume if isinstance(raw_resume, MasterResume) else dict(raw_resume))
        profile = params.get("profile")
        if profile:
            apply_profile(res_obj, str(profile))
        export_docx(res_obj, out_p)
        return ok(output_path=out_p)

    @api_method
    def resume_analyze_ats(self, params: dict[str, Any]) -> dict[str, Any]:
        # Analyze keyword matching score against job description.
        require(params, "resume", "job_description")
        raw_resume = params["resume"]
        res_obj = resume_from_dict(raw_resume if isinstance(raw_resume, MasterResume) else dict(raw_resume))
        job_desc = str(params["job_description"])
        res = analyze_ats_match(res_obj, job_desc)
        score = float(res.get("score", 0))
        matched = [kw for kw, _ in res.get("matched", [])]
        missing = [kw for kw, _ in res.get("missing", [])]
        return ok(score=round(score, 1), matched_keywords=matched, missing_keywords=missing)

    @api_method
    def resume_save_profile(self, params: dict[str, Any]) -> dict[str, Any]:
        # Save tailored profile configuration inside master resume.
        require(params, "resume", "profile_name")
        raw_resume = params["resume"]
        res_obj = resume_from_dict(raw_resume if isinstance(raw_resume, MasterResume) else dict(raw_resume))
        save_profile(res_obj, str(params["profile_name"]))
        return ok(resume=resume_to_dict(res_obj))

    @api_method
    def resume_apply_profile(self, params: dict[str, Any]) -> dict[str, Any]:
        # Apply profile filter to master resume.
        require(params, "resume", "profile_name")
        raw_resume = params["resume"]
        res_obj = resume_from_dict(raw_resume if isinstance(raw_resume, MasterResume) else dict(raw_resume))
        apply_profile(res_obj, str(params["profile_name"]))
        return ok(resume=resume_to_dict(res_obj))
