"""Integration tests for WebApi bridge methods."""
from __future__ import annotations

import os
import tempfile
import unittest

from PIL import Image
import pymupdf

from app.web.api import WebApi


class WebApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.api = WebApi()

    def test_get_apps_returns_all_home_apps(self) -> None:
        apps = self.api.get_apps()
        self.assertGreaterEqual(len(apps), 20)
        ids = {app["id"] for app in apps}
        self.assertIn("pdf", ids)
        self.assertIn("images", ids)
        self.assertIn("media", ids)
        self.assertIn("model3d", ids)
        self.assertIn("converter", ids)

    def test_settings_and_theme_palette(self) -> None:
        palette = self.api.get_theme_palette("dark")
        self.assertIn("background", palette)
        self.assertIn("accent", palette)

        self.api.set_setting("test_key", "test_val")
        val = self.api.get_setting("test_key")
        self.assertEqual(val, "test_val")

    def test_search_tools(self) -> None:
        results = self.api.search_tools("pdf")
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    def test_pdf_operations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = os.path.join(tmp_dir, "test.pdf")
            doc = pymupdf.open()
            page = doc.new_page(width=300, height=300)
            page.insert_text((50, 50), "Hello FOSSEverything")
            doc.save(pdf_path)
            doc.close()

            info = self.api.pdf_open_doc(pdf_path)
            self.assertTrue(info.get("success"))
            self.assertEqual(info.get("page_count"), 1)

            render = self.api.pdf_render_page(pdf_path, 0, dpi=72)
            self.assertTrue(render.get("success"))
            self.assertTrue(render["data_url"].startswith("data:image/png;base64,"))

            rotated_path = os.path.join(tmp_dir, "rotated.pdf")
            res_rot = self.api.pdf_rotate_page(pdf_path, 0, 90, rotated_path)
            self.assertTrue(res_rot.get("success"))

            num_path = os.path.join(tmp_dir, "numbered.pdf")
            res_num = self.api.pdf_add_page_numbers(pdf_path, num_path)
            self.assertTrue(res_num.get("success"))

            watermarked_path = os.path.join(tmp_dir, "watermarked.pdf")
            res_wm = self.api.pdf_watermark(pdf_path, watermarked_path, "CONFIDENTIAL")
            self.assertTrue(res_wm.get("success"))

            merged_path = os.path.join(tmp_dir, "merged.pdf")
            res_merge = self.api.pdf_merge([pdf_path, rotated_path], merged_path)
            self.assertTrue(res_merge.get("success"))

            # Test in-place rotate and delete
            res_rot_inplace = self.api.pdf_rotate_page(merged_path, 0, 90)
            self.assertTrue(res_rot_inplace.get("success"))

            res_ext_page = self.api.pdf_extract_single_page(merged_path, 0, os.path.join(tmp_dir, "single.pdf"))
            self.assertTrue(res_ext_page.get("success"))

            res_annot = self.api.pdf_save_annotated_page(merged_path, 0, [{"type": "rect", "x": 10, "y": 10, "w": 50, "h": 50}], os.path.join(tmp_dir, "annot.pdf"))
            self.assertTrue(res_annot.get("success"))

            res_reorder = self.api.pdf_reorder_pages(merged_path, [1, 0], os.path.join(tmp_dir, "reordered.pdf"))
            self.assertTrue(res_reorder.get("success"))

            res_split = self.api.pdf_split(merged_path, "", tmp_dir)
            self.assertTrue(res_split.get("success"))
            self.assertIn("files", res_split)

            res_del_inplace = self.api.pdf_delete_page(merged_path, 1)
            self.assertTrue(res_del_inplace.get("success"))

    def test_image_operations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            img_path = os.path.join(tmp_dir, "test.png")
            img = Image.new("RGB", (60, 40), color="blue")
            img.save(img_path)

            rot_path = os.path.join(tmp_dir, "rotated.png")
            res_r = self.api.image_rotate(img_path, rot_path, 90)
            self.assertTrue(res_r.get("success"))

            res_adj = self.api.image_adjust(img_path, rot_path, brightness=1.1, contrast=1.1)
            self.assertTrue(res_adj.get("success"))

            resized_path = os.path.join(tmp_dir, "resized.png")
            res_resize = self.api.image_resize(img_path, resized_path, 30, 20)
            self.assertTrue(res_resize.get("success"))

    def test_text_and_encoding_operations(self) -> None:
        res_case = self.api.text_case_transform("hello world", "upper")
        self.assertEqual(res_case.get("result"), "HELLO WORLD")

        wc_res = self.api.word_counter_analyze("Five words are in here.")
        self.assertEqual(wc_res["words"], 5)

        wc_rep = self.api.word_counter_generate_report("Five words are in here.")
        self.assertIn("report", wc_rep)
        self.assertIn("Words:", wc_rep["report"])

        with tempfile.TemporaryDirectory() as tmp_dir:
            sample_doc = os.path.join(tmp_dir, "sample_doc.txt")
            self.api.save_file("Alpha beta gamma delta epsilon.", sample_doc)
            file_res = self.api.word_counter_analyze_file(sample_doc)
            self.assertEqual(file_res["words"], 5)
            self.assertIn("Alpha beta", file_res["text"])

            read_res = self.api.read_file_text(sample_doc)
            self.assertEqual(read_res["text"], "Alpha beta gamma delta epsilon.")

        enc_res = self.api.encoding_transform("hello", "base64", "encode")
        self.assertEqual(enc_res.get("result"), "aGVsbG8=")

    def test_hash_and_data_operations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, "sample.txt")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("abc")
            h = self.api.compute_file_hash(file_path, "sha256")
            sha256_val = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
            self.assertEqual(h.get("hash"), sha256_val)

            v_res = self.api.verify_hash(file_path, sha256_val)
            self.assertTrue(v_res.get("matches"))
            self.assertEqual(v_res.get("algorithm"), "sha256")

            man_res = self.api.generate_manifest(tmp_dir)
            self.assertTrue(man_res.get("success"))
            self.assertEqual(man_res.get("file_count"), 1)

        fmt_res = self.api.format_json('{"b":2,"a":1}', indent=2)
        self.assertIn("formatted", fmt_res)
        self.assertIn('"a": 1', fmt_res["formatted"])

        js_res = self.api.format_js("function test(){return 1;}")
        self.assertIn("formatted", js_res)

    def test_model3d_operations(self) -> None:
        import trimesh
        with tempfile.TemporaryDirectory() as tmp_dir:
            stl_path = os.path.join(tmp_dir, "box.stl")
            mesh = trimesh.creation.box(extents=(10.0, 10.0, 10.0))
            mesh.export(stl_path)

            load_res = self.api.model3d_load_mesh(stl_path)
            self.assertTrue(load_res.get("success"))
            self.assertEqual(load_res["face_count"], 12)
            self.assertGreater(len(load_res["vertices"]), 0)

            repair_path = os.path.join(tmp_dir, "repaired.stl")
            rep_res = self.api.model3d_repair_mesh(stl_path, repair_path)
            self.assertTrue(rep_res.get("success"))

            scale_path = os.path.join(tmp_dir, "scaled.stl")
            scale_res = self.api.model3d_scale_mesh(stl_path, 2.0, scale_path)
            self.assertTrue(scale_res.get("success"))

            cut_path = os.path.join(tmp_dir, "cut.stl")
            cut_res = self.api.model3d_cut_mesh(stl_path, "z", 0.5, cut_path, cap=True)
            self.assertTrue(cut_res.get("success"))
            self.assertTrue(os.path.isfile(cut_path))

            export_path = os.path.join(tmp_dir, "exported.obj")
            exp_res = self.api.model3d_export(stl_path, export_path, "obj")
            self.assertTrue(exp_res.get("success"))
            self.assertTrue(os.path.isfile(export_path))

            meas_res = self.api.model3d_measure([0.0, 0.0, 0.0], [3.0, 4.0, 0.0])
            self.assertTrue(meas_res.get("success"))
            self.assertAlmostEqual(meas_res.get("distance", 0.0), 5.0, places=3)

    def test_converter_and_qr_operations(self) -> None:
        targets = self.api.converter_available_targets(".png")
        self.assertIn("JPEG", targets)
        self.assertEqual(self.api.select_directory(), "")

        with tempfile.TemporaryDirectory() as tmp_dir:
            src_png = os.path.join(tmp_dir, "test.png")
            Image.new("RGB", (20, 20), color="red").save(src_png)
            out_dir = os.path.join(tmp_dir, "converted")

            res = self.api.convert_file(src_png, "jpg", out_dir)
            self.assertTrue(res.get("success"))
            self.assertTrue(os.path.isfile(res["output_path"]))

            batch_res = self.api.converter_batch([src_png], "webp", out_dir)
            self.assertTrue(batch_res.get("success"))
            self.assertEqual(batch_res.get("converted"), 1)

            err_res = self.api.convert_file("nonexistent_file.xyz", "jpg", out_dir)
            self.assertIn("error", err_res)

        qr_res = self.api.generate_qr("https://fosseverything.org")
        self.assertTrue(qr_res.get("data_url", "").startswith("data:image/png;base64,"))

    def test_archive_and_renamer_operations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            f1 = os.path.join(tmp_dir, "file1.txt")
            with open(f1, "w", encoding="utf-8") as f:
                f.write("test content")

            zip_path = os.path.join(tmp_dir, "archive.zip")
            arc_res = self.api.archive_create([f1], zip_path, fmt="zip")
            self.assertTrue(arc_res.get("success"))

            list_res = self.api.archive_list(zip_path)
            self.assertTrue(list_res.get("success"))
            self.assertGreater(len(list_res["entries"]), 0)

            test_res = self.api.archive_test(zip_path)
            self.assertTrue(test_res.get("success"))

            preview_res = self.api.renamer_preview([f1], pattern="file", replace="doc", mode="replace")
            self.assertEqual(len(preview_res["preview"]), 1)

            apply_res = self.api.renamer_apply()
            self.assertTrue(apply_res.get("success"))
            self.assertEqual(apply_res.get("count"), 1)

            undo_res = self.api.renamer_undo()
            self.assertTrue(undo_res.get("success"))
            self.assertEqual(undo_res.get("count"), 1)

    def test_network_monitor_operations(self) -> None:
        res = self.api.get_network_connections()
        self.assertIn("connections", res)
        self.assertIsInstance(res["connections"], list)


    def test_palette_and_save_file_operations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            img_path = os.path.join(tmp_dir, "pal_test.png")
            img = Image.new("RGB", (50, 50), color="red")
            img.save(img_path)

            pal_res = self.api.palette_extract(img_path, num_colors=4)
            self.assertIn("colors", pal_res)
            self.assertGreater(len(pal_res["colors"]), 0)

            # Test save_file
            out_json = os.path.join(tmp_dir, "pal.json")
            save_res = self.api.save_file('{"test": true}', out_json)
            self.assertTrue(save_res.get("success"))
            self.assertTrue(os.path.isfile(out_json))

            # Test palette_export_gpl with file path
            out_gpl = os.path.join(tmp_dir, "pal.gpl")
            gpl_res = self.api.palette_export_gpl(pal_res["colors"], out_gpl)
            self.assertTrue(gpl_res.get("success"))
            self.assertTrue(os.path.isfile(out_gpl))

    def test_collage_operations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            p1 = os.path.join(tmp_dir, "img1.png")
            p2 = os.path.join(tmp_dir, "img2.png")
            Image.new("RGB", (40, 40), color="red").save(p1)
            Image.new("RGB", (40, 40), color="blue").save(p2)

            out_path = os.path.join(tmp_dir, "collage.png")
            res = self.api.collage_create([p1, p2], out_path, columns=2, spacing=10, radius=5, aspect="4:3")
            self.assertTrue(res.get("success"))
            self.assertTrue(os.path.isfile(out_path))
            self.assertTrue(res.get("data_url", "").startswith("data:image/"))

            prev_res = self.api.collage_preview([p1, p2], columns=2, spacing=10, radius=5, aspect="4:3")
            self.assertTrue(prev_res.get("success"))
            self.assertTrue(prev_res.get("data_url", "").startswith("data:image/"))

    def test_metadata_operations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            source = os.path.join(tmp_dir, "test.pdf")
            doc = pymupdf.open()
            doc.new_page()
            doc.set_metadata({"title": "Test Title", "author": "Tester"})
            doc.save(source)
            doc.close()

            inspect_res = self.api.metadata_inspect(source)
            self.assertEqual(inspect_res.get("fields", {}).get("title"), "Test Title")

            export_path = os.path.join(tmp_dir, "meta.json")
            export_res = self.api.metadata_export(source, export_path)
            self.assertTrue(export_res.get("success"))
            self.assertTrue(os.path.exists(export_path))

            strip_path = os.path.join(tmp_dir, "clean.pdf")
            strip_res = self.api.metadata_strip(source, strip_path)
            self.assertTrue(strip_res.get("success"))


if __name__ == "__main__":
    unittest.main()

