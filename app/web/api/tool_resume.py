from pathlib import Path
from typing import Any

from app.features.resume.ops import (
    MasterResume,
    analyze_ats_match,
    apply_date_format,
    apply_profile,
    create_sample_master_resume,
    estimate_docx_height_pt,
    export_docx,
    export_html,
    export_markdown,
    export_pdf,
    export_resume_file,
    fit_docx_font_pt,
    load_resume_file,
    render_resume_preview_pages,
    resume_from_dict,
    resume_to_dict,
    save_profile,
    save_resume_file,
)
from app.web.api.result import api_method, ok, require


def _prepare_resume(params: dict[str, Any]) -> MasterResume:
    # Build the resume from params, applying the tailored profile and date format.
    res_obj = resume_from_dict(params["resume"] if isinstance(params["resume"], MasterResume) else dict(params["resume"]))
    profile = params.get("profile")
    if profile:
        apply_profile(res_obj, str(profile))
    date_format = params.get("date_format")
    if date_format:
        res_obj = apply_date_format(res_obj, str(date_format))
    return res_obj


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
        res_obj = _prepare_resume(params)
        font_pt = float(params.get("font_pt", 11.0))
        dpi = int(params.get("dpi", 160))
        preview_data = render_resume_preview_pages(res_obj, dpi=dpi, font_pt=font_pt)
        return ok(**preview_data)

    @api_method
    def resume_render_html(self, params: dict[str, Any]) -> dict[str, Any]:
        # Render HTML document preview for resume profile.
        require(params, "resume")
        res_obj = _prepare_resume(params)
        layout = str(params.get("layout", "single"))
        accent = str(params.get("accent_color", "#000000"))
        html_out = export_html(res_obj, layout=layout, accent_color=accent)
        return ok(html=html_out)

    @api_method
    def resume_export_markdown(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export resume content as structured Markdown.
        require(params, "resume")
        res_obj = _prepare_resume(params)
        md_text = export_markdown(res_obj)
        out_p = params.get("output_path")
        if out_p:
            Path(str(out_p)).write_text(md_text, encoding="utf-8")
        return ok(markdown=md_text, output_path=out_p)

    @api_method
    def resume_export_pdf(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export resume profile to formatted PDF document.
        require(params, "resume", "output_path")
        out_p = str(params["output_path"])
        export_pdf(_prepare_resume(params), out_p)
        return ok(output_path=out_p)

    @api_method
    def resume_export_docx(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export resume profile to a one-page Word DOCX document.
        require(params, "resume", "output_path")
        out_p = str(params["output_path"])
        export_docx(_prepare_resume(params), out_p)
        return ok(output_path=out_p)

    @api_method
    def resume_export(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export resume in the format given by the output path extension (docx, pdf, txt).
        require(params, "resume", "output_path")
        out_p = str(params["output_path"])
        font_pt = float(params.get("font_pt", 11.0))
        info = export_resume_file(_prepare_resume(params), out_p, font_pt=font_pt)
        return ok(output_path=out_p, **info)

    @api_method
    def resume_docx_fit(self, params: dict[str, Any]) -> dict[str, Any]:
        # Report the font size at which the DOCX export fits on one page.
        require(params, "resume")
        res_obj = _prepare_resume(params)
        font_pt = float(params.get("font_pt", 11.0))
        body_pt = fit_docx_font_pt(res_obj, max(font_pt - 0.5, 8.0))
        height_pt = estimate_docx_height_pt(res_obj, body_pt)
        return ok(font_pt=body_pt + 0.5, height_pt=round(height_pt, 1))

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
