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
        res = self.api.get_apps({})
        self.assertTrue(res.get("ok"))
        apps = res["apps"]
        self.assertGreaterEqual(len(apps), 20)
        ids = {app["id"] for app in apps}
        self.assertIn("pdf", ids)
        self.assertIn("images", ids)
        self.assertIn("compressor", ids)
        self.assertIn("model3d", ids)
        self.assertIn("converter", ids)

    def test_settings_and_theme_palette(self) -> None:
        res = self.api.get_theme_palette({"theme_name": "dark"})
        self.assertTrue(res.get("ok"))
        self.assertIn("background", res)
        self.assertIn("accent", res)

        set_res = self.api.set_setting({"key": "test_key", "value": "test_val"})
        self.assertTrue(set_res.get("ok"))
        get_res = self.api.get_setting({"key": "test_key"})
        self.assertTrue(get_res.get("ok"))
        self.assertEqual(get_res.get("value"), "test_val")

        reset_defaults_res = self.api.reset_settings_defaults({})
        self.assertTrue(reset_defaults_res.get("ok"))
        self.assertEqual(
            reset_defaults_res.get("message"), "Settings reset to defaults"
        )
        self.assertEqual(self.api.get_setting({"key": "theme"}).get("value"), "dark")
        self.assertIsNone(self.api.get_setting({"key": "test_key"}).get("value"))

    def test_search_tools(self) -> None:
        res = self.api.search_tools({"query": "pdf"})
        self.assertTrue(res.get("ok"))
        self.assertIsInstance(res.get("results"), list)
        self.assertGreater(len(res["results"]), 0)

    def test_pdf_operations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = os.path.join(tmp_dir, "test.pdf")
            doc = pymupdf.open()
            page = doc.new_page(width=300, height=300)
            page.insert_text((50, 50), "Hello FOSSEverything")
            doc.save(pdf_path)
            doc.close()

            info = self.api.pdf_open_doc({"file_path": pdf_path})
            self.assertTrue(info.get("ok"))
            self.assertEqual(info.get("page_count"), 1)

            render = self.api.pdf_render_page(
                {"file_path": pdf_path, "page_number": 0, "dpi": 72}
            )
            self.assertTrue(render.get("ok"))
            self.assertTrue(render["data_url"].startswith("data:image/png;base64,"))

            rotated_path = os.path.join(tmp_dir, "rotated.pdf")
            res_rot = self.api.pdf_rotate_page(
                {
                    "file_path": pdf_path,
                    "page_number": 0,
                    "degrees": 90,
                    "output_path": rotated_path,
                }
            )
            self.assertTrue(res_rot.get("ok"))

            num_path = os.path.join(tmp_dir, "numbered.pdf")
            res_num = self.api.pdf_add_page_numbers(
                {"file_path": pdf_path, "output_path": num_path}
            )
            self.assertTrue(res_num.get("ok"))

            watermarked_path = os.path.join(tmp_dir, "watermarked.pdf")
            res_wm = self.api.pdf_watermark(
                {
                    "file_path": pdf_path,
                    "output_path": watermarked_path,
                    "text": "CONFIDENTIAL",
                }
            )
            self.assertTrue(res_wm.get("ok"))

            merged_path = os.path.join(tmp_dir, "merged.pdf")
            res_merge = self.api.pdf_merge(
                {"file_paths": [pdf_path, rotated_path], "output_path": merged_path}
            )
            self.assertTrue(res_merge.get("ok"))

            res_rot_inplace = self.api.pdf_rotate_page(
                {"file_path": merged_path, "page_number": 0, "degrees": 90}
            )
            self.assertTrue(res_rot_inplace.get("ok"))

            res_rot_multi = self.api.pdf_rotate_pages(
                {"file_path": merged_path, "pages": [0, 1], "degrees": 90}
            )
            self.assertTrue(res_rot_multi.get("ok"))
            self.assertEqual(res_rot_multi.get("rotated_count"), 2)

            single_path = os.path.join(tmp_dir, "single.pdf")
            res_ext_page = self.api.pdf_extract_single_page(
                {"file_path": merged_path, "page_number": 0, "output_path": single_path}
            )
            self.assertTrue(res_ext_page.get("ok"))

            annot_path = os.path.join(tmp_dir, "annot.pdf")
            res_annot = self.api.pdf_save_annotated_page(
                {
                    "file_path": merged_path,
                    "page_number": 0,
                    "annotations": [
                        {"type": "rect", "x": 10, "y": 10, "w": 50, "h": 50}
                    ],
                    "output_path": annot_path,
                }
            )
            self.assertTrue(res_annot.get("ok"))

            reorder_path = os.path.join(tmp_dir, "reordered.pdf")
            res_reorder = self.api.pdf_reorder_pages(
                {"file_path": merged_path, "order": [1, 0], "output_path": reorder_path}
            )
            self.assertTrue(res_reorder.get("ok"))

            res_split = self.api.pdf_split(
                {"file_path": merged_path, "output_dir": tmp_dir}
            )
            self.assertTrue(res_split.get("ok"))
            self.assertIn("files", res_split)

            res_del_inplace = self.api.pdf_delete_page(
                {"file_path": merged_path, "page_number": 1}
            )
            self.assertTrue(res_del_inplace.get("ok"))

    def test_image_operations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            img_path = os.path.join(tmp_dir, "test.png")
            img = Image.new("RGB", (60, 40), color="blue")
            img.save(img_path)

            rot_path = os.path.join(tmp_dir, "rotated.png")
            res_r = self.api.image_rotate(
                {"file_path": img_path, "output_path": rot_path, "degrees": 90}
            )
            self.assertTrue(res_r.get("ok"))

            res_adj = self.api.image_adjust(
                {
                    "file_path": img_path,
                    "output_path": rot_path,
                    "brightness": 1.1,
                    "contrast": 1.1,
                }
            )
            self.assertTrue(res_adj.get("ok"))

            resized_path = os.path.join(tmp_dir, "resized.png")
            res_resize = self.api.image_resize(
                {
                    "file_path": img_path,
                    "output_path": resized_path,
                    "width": 30,
                    "height": 20,
                }
            )
            self.assertTrue(res_resize.get("ok"))

    def test_text_and_encoding_operations(self) -> None:
        res_case = self.api.text_case_transform(
            {"text": "hello world", "mode": "upper"}
        )
        self.assertEqual(res_case.get("result"), "HELLO WORLD")

        wc_res = self.api.word_counter_analyze({"text": "Five words are in here."})
        self.assertEqual(wc_res["words"], 5)

        wc_rep = self.api.word_counter_generate_report(
            {"text": "Five words are in here."}
        )
        self.assertIn("report", wc_rep)
        self.assertIn("Words:", wc_rep["report"])

        with tempfile.TemporaryDirectory() as tmp_dir:
            sample_doc = os.path.join(tmp_dir, "sample_doc.txt")
            self.api.save_file(
                {"file_path": sample_doc, "content": "Alpha beta gamma delta epsilon."}
            )
            file_res = self.api.word_counter_analyze_file({"file_path": sample_doc})
            self.assertEqual(file_res["words"], 5)
            self.assertIn("Alpha beta", file_res["text"])

            read_res = self.api.read_file_text({"file_path": sample_doc})
            self.assertEqual(read_res["text"], "Alpha beta gamma delta epsilon.")

        enc_res = self.api.encoding_transform(
            {"text": "hello", "method": "base64", "direction": "encode"}
        )
        self.assertEqual(enc_res.get("result"), "aGVsbG8=")

    def test_hash_and_data_operations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, "sample.txt")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("abc")
            h = self.api.compute_file_hash(
                {"file_path": file_path, "algorithm": "sha256"}
            )
            sha256_val = (
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
            )
            self.assertEqual(h.get("hash"), sha256_val)

            v_res = self.api.verify_hash(
                {"file_path": file_path, "expected_hash": sha256_val}
            )
            self.assertTrue(v_res.get("matches"))
            self.assertEqual(v_res.get("algorithm"), "sha256")

            man_res = self.api.generate_manifest({"directory_path": tmp_dir})
            self.assertTrue(man_res.get("ok"))
            self.assertEqual(man_res.get("count"), 1)

        fmt_res = self.api.format_json({"content": '{"b":2,"a":1}', "indent": 2})
        self.assertTrue(fmt_res.get("ok"))
        self.assertIn('"a": 1', fmt_res["result"])

        js_res = self.api.format_js({"content": "function test(){return 1;}"})
        self.assertTrue(js_res.get("ok"))

        # Test structure inspection.
        struct_res = self.api.data_inspect_structure(
            {"content": '{"name": "Tool", "count": 5}'}
        )
        self.assertTrue(struct_res.get("ok"))
        self.assertEqual(struct_res.get("format"), "JSON")
        self.assertIn("root", struct_res)

        with tempfile.TemporaryDirectory() as tmp_dir:
            import struct as pystruct

            h5_path = os.path.join(tmp_dir, "test.h5")
            sig = b"\x89HDF\r\n\x1a\n"
            sb = sig + bytes([0, 0, 0, 0, 0, 8, 8, 0])
            sb += pystruct.pack(
                "<HHIQQQQ", 4, 16, 0, 0, 0xFFFFFFFFFFFFFFFF, 512, 0xFFFFFFFFFFFFFFFF
            )
            sb += pystruct.pack("<QQIIQQ", 0, 96, 0, 0, 0, 0)
            with open(h5_path, "wb") as f:
                f.write(sb)
            h5_res = self.api.data_inspect_structure({"file_path": h5_path})
            self.assertTrue(h5_res.get("ok"))
            self.assertEqual(h5_res.get("format"), "HDF5")
            self.assertIn("root", h5_res)

            csv_slice_out = os.path.join(tmp_dir, "slice.csv")
            slice_res = self.api.data_hdf5_export_slice(
                {
                    "file_path": h5_path,
                    "dataset_path": "/dataset_1",
                    "slice_spec": "0:5",
                    "output_path": csv_slice_out,
                    "format": "csv",
                }
            )
            self.assertTrue(slice_res.get("ok"))
            self.assertTrue(os.path.isfile(csv_slice_out))
            self.assertEqual(slice_res.get("format"), "CSV")

            npy_slice_out = os.path.join(tmp_dir, "slice.npy")
            npy_res = self.api.data_hdf5_export_slice(
                {
                    "file_path": h5_path,
                    "dataset_path": "/dataset_1",
                    "slice_spec": "0:5",
                    "output_path": npy_slice_out,
                    "format": "npy",
                }
            )
            self.assertTrue(npy_res.get("ok"))
            self.assertTrue(os.path.isfile(npy_slice_out))

        # Test table operations with custom delimiter.
        md_res = self.api.data_csv_to_table({"content": "A;B\n1;2", "delimiter": ";"})
        self.assertTrue(md_res.get("ok"))
        self.assertIn("| A | B |", md_res.get("result", ""))

        csv_res = self.api.data_table_to_csv(
            {"content": md_res["result"], "delimiter": "\t"}
        )
        self.assertTrue(csv_res.get("ok"))
        self.assertIn("A\tB", csv_res.get("result", ""))

        chg_res = self.api.data_change_delimiter(
            {"content": "A,B\n1,2", "from_delimiter": ",", "to_delimiter": ";"}
        )
        self.assertTrue(chg_res.get("ok"))
        self.assertIn("A;B", chg_res.get("result", ""))

        # Test random generator options.
        hex_res = self.api.data_random_value(
            {"category": "hex", "length": 32, "count": 2}
        )
        self.assertTrue(hex_res.get("ok"))
        self.assertEqual(len(hex_res.get("values", [])), 2)
        self.assertEqual(len(hex_res.get("values", [])[0]), 32)

        lorem_res = self.api.data_random_value({"category": "lorem", "length": 8})
        self.assertTrue(lorem_res.get("ok"))
        self.assertIn(" ", lorem_res.get("value", ""))

        # Test units conversion swap.
        u_forward = self.api.data_convert_units(
            {"value": 1.0, "source_unit": "m", "target_unit": "cm"}
        )
        self.assertTrue(u_forward.get("ok"))
        self.assertEqual(u_forward.get("result"), 100.0)
        u_swap = self.api.data_convert_units(
            {"value": 100.0, "source_unit": "cm", "target_unit": "m"}
        )
        self.assertTrue(u_swap.get("ok"))
        self.assertEqual(u_swap.get("result"), 1.0)

    def test_model3d_operations(self) -> None:
        import trimesh

        with tempfile.TemporaryDirectory() as tmp_dir:
            stl_path = os.path.join(tmp_dir, "box.stl")
            mesh = trimesh.creation.box(extents=(10.0, 10.0, 10.0))
            mesh.export(stl_path)

            load_res = self.api.model3d_load_mesh({"file_path": stl_path})
            self.assertTrue(load_res.get("ok"))
            self.assertEqual(load_res["face_count"], 12)
            self.assertGreater(len(load_res["vertices"]), 0)

            repair_path = os.path.join(tmp_dir, "repaired.stl")
            rep_res = self.api.model3d_repair_mesh(
                {"file_path": stl_path, "output_path": repair_path}
            )
            self.assertTrue(rep_res.get("ok"))

            scale_path = os.path.join(tmp_dir, "scaled.stl")
            scale_res = self.api.model3d_scale_mesh(
                {"file_path": stl_path, "factor": 2.0, "output_path": scale_path}
            )
            self.assertTrue(scale_res.get("ok"))

            cut_res = self.api.model3d_cut_mesh(
                {
                    "file_path": stl_path,
                    "planes": [{"origin": [0, 0, 0], "normal": [0, 0, 1]}],
                    "output_dir": tmp_dir,
                }
            )
            self.assertTrue(cut_res.get("ok"))
            self.assertGreater(len(cut_res["pieces"]), 0)

            export_path = os.path.join(tmp_dir, "exported.obj")
            exp_res = self.api.model3d_export(
                {"file_path": stl_path, "output_path": export_path, "format": "obj"}
            )
            self.assertTrue(exp_res.get("ok"))
            self.assertTrue(os.path.isfile(export_path))

            meas_res = self.api.model3d_measure(
                {"p1": [0.0, 0.0, 0.0], "p2": [3.0, 4.0, 0.0]}
            )
            self.assertTrue(meas_res.get("ok"))
            self.assertAlmostEqual(meas_res.get("distance", 0.0), 5.0, places=3)

            centered_path = os.path.join(tmp_dir, "centered.stl")
            center_res = self.api.model3d_center_origin(
                {"file_path": stl_path, "output_path": centered_path}
            )
            self.assertTrue(center_res.get("ok"))
            self.assertTrue(os.path.isfile(centered_path))

    def test_converter_summary_isolated(self) -> None:
        # Verify converter summary execution and error handling.
        with tempfile.TemporaryDirectory() as tmp_dir:
            src_png = os.path.join(tmp_dir, "test.png")
            Image.new("RGB", (20, 20), color="red").save(src_png)

            res = self.api.converter_summary(
                {"file_path": src_png, "target_format": "PDF (Searchable)"}
            )
            self.assertTrue(res.get("ok"))
            self.assertIn("invisible OCR text layer", res.get("summary", ""))

            err_res = self.api.converter_summary({"file_path": src_png})
            self.assertFalse(err_res.get("ok"))

    def test_converter_convert_file_isolated(self) -> None:
        # Verify single file conversion execution and error handling.
        # Ensure it works for valid formats and errors on missing files.
        with tempfile.TemporaryDirectory() as tmp_dir:
            src_png = os.path.join(tmp_dir, "test.png")
            Image.new("RGB", (20, 20), color="red").save(src_png)
            out_file = os.path.join(tmp_dir, "converted.jpg")

            res = self.api.converter_convert_file(
                {"file_path": src_png, "target_format": "jpg", "output_path": out_file}
            )
            self.assertTrue(res.get("ok"))
            self.assertTrue(os.path.isfile(res.get("output_path", "")))

            err_res = self.api.converter_convert_file(
                {"file_path": "nonexistent_file.xyz", "target_format": "jpg"}
            )
            self.assertFalse(err_res.get("ok"))

    def test_converter_batch_convert_isolated(self) -> None:
        # Verify batch conversion execution and error handling.
        # Ensure it works for valid inputs and errors on missing items.
        with tempfile.TemporaryDirectory() as tmp_dir:
            f_path = os.path.join(tmp_dir, "doc.txt")
            with open(f_path, "w", encoding="utf-8") as f:
                f.write("batch content")

            params = {"items": [{"input_path": f_path, "target_format": "md"}]}
            res = self.api.converter_batch_convert(params)
            self.assertTrue(res.get("ok"))
            self.assertIn("Converted 1 file", res.get("summary", ""))

            bad_res = self.api.converter_batch_convert({})
            self.assertFalse(bad_res.get("ok"))

    def test_converter_and_qr_operations(self) -> None:
        targets_res = self.api.converter_available_targets({"file_path": "sample.png"})
        self.assertTrue(targets_res.get("ok"))
        self.assertIn("JPEG", targets_res["targets"])

        with tempfile.TemporaryDirectory() as tmp_dir:
            src_png = os.path.join(tmp_dir, "test.png")
            Image.new("RGB", (20, 20), color="red").save(src_png)
            out_file = os.path.join(tmp_dir, "converted.jpg")

            res = self.api.convert_file(
                {"file_path": src_png, "target_format": "jpg", "output_path": out_file}
            )
            self.assertTrue(res.get("ok"))
            self.assertTrue(os.path.isfile(res["output_path"]))

            batch_res = self.api.converter_batch(
                {"items": [{"source_path": src_png, "target_format": "webp"}]}
            )
            self.assertTrue(batch_res.get("ok"))

            err_res = self.api.convert_file(
                {"file_path": "nonexistent_file.xyz", "target_format": "jpg"}
            )
            self.assertFalse(err_res.get("ok"))

        qr_res = self.api.generate_qr({"payload": "https://fosseverything.org"})
        self.assertTrue(qr_res.get("data_url", "").startswith("data:image/png;base64,"))

    def test_archive_and_renamer_operations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            f1 = os.path.join(tmp_dir, "file1.txt")
            with open(f1, "w", encoding="utf-8") as f:
                f.write("test content")

            zip_path = os.path.join(tmp_dir, "archive.zip")
            arc_res = self.api.archive_create(
                {"sources": [f1], "output_path": zip_path, "format": "zip"}
            )
            self.assertTrue(arc_res.get("ok"))

            list_res = self.api.archive_list({"archive_path": zip_path})
            self.assertTrue(list_res.get("ok"))
            self.assertGreater(len(list_res["contents"]), 0)

            test_res = self.api.archive_test({"archive_path": zip_path})
            self.assertTrue(test_res.get("ok"))

            preview_res = self.api.renamer_preview(
                {
                    "file_paths": [f1],
                    "mode": "find_replace",
                    "options": {"find": "file", "replace": "doc"},
                }
            )
            self.assertTrue(preview_res.get("ok"))
            self.assertEqual(len(preview_res["entries"]), 1)

            apply_res = self.api.renamer_apply(
                {
                    "file_paths": [f1],
                    "mode": "find_replace",
                    "options": {"find": "file", "replace": "doc"},
                }
            )
            self.assertTrue(apply_res.get("ok"))

    def test_network_monitor_operations(self) -> None:
        res = self.api.get_network_connections({})
        self.assertTrue(res.get("ok"))
        self.assertIn("connections", res)
        self.assertIsInstance(res["connections"], list)

    def test_palette_and_save_file_operations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            img_path = os.path.join(tmp_dir, "pal_test.png")
            img = Image.new("RGB", (50, 50), color="red")
            img.save(img_path)

            pal_res = self.api.palette_extract(
                {"image_path": img_path, "num_colors": 4}
            )
            self.assertTrue(pal_res.get("ok"))
            self.assertIn("palette", pal_res)
            self.assertGreater(len(pal_res["palette"]), 0)

            out_json = os.path.join(tmp_dir, "pal.json")
            save_res = self.api.save_file(
                {"file_path": out_json, "content": '{"test": true}'}
            )
            self.assertTrue(save_res.get("ok"))
            self.assertTrue(os.path.isfile(out_json))

            out_gpl = os.path.join(tmp_dir, "pal.gpl")
            colors = [p["hex"] for p in pal_res["palette"]]
            gpl_res = self.api.palette_export_gpl(
                {"colors": colors, "output_path": out_gpl}
            )
            self.assertTrue(gpl_res.get("ok"))
            self.assertTrue(os.path.isfile(out_gpl))

    def test_collage_operations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            p1 = os.path.join(tmp_dir, "img1.png")
            p2 = os.path.join(tmp_dir, "img2.png")
            Image.new("RGB", (40, 40), color="red").save(p1)
            Image.new("RGB", (40, 40), color="blue").save(p2)

            out_path = os.path.join(tmp_dir, "collage.png")
            res = self.api.collage_create(
                {"image_paths": [p1, p2], "output_path": out_path, "columns": 2}
            )
            self.assertTrue(res.get("ok"))
            self.assertTrue(os.path.isfile(out_path))

            prev_res = self.api.collage_preview({"image_paths": [p1, p2], "columns": 2})
            self.assertTrue(prev_res.get("ok"))
            self.assertTrue(prev_res.get("data_url", "").startswith("data:image/"))

    def test_metadata_operations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            source = os.path.join(tmp_dir, "test.pdf")
            doc = pymupdf.open()
            doc.new_page()
            doc.set_metadata({"title": "Test Title", "author": "Tester"})
            doc.save(source)
            doc.close()

            inspect_res = self.api.metadata_inspect({"file_path": source})
            self.assertTrue(inspect_res.get("ok"))

            export_path = os.path.join(tmp_dir, "meta.json")
            export_res = self.api.metadata_export(
                {"file_path": source, "output_path": export_path}
            )
            self.assertTrue(export_res.get("ok"))
            self.assertTrue(os.path.exists(export_path))

            strip_path = os.path.join(tmp_dir, "clean.pdf")
            strip_res = self.api.metadata_strip(
                {"file_path": source, "output_path": strip_path}
            )
            self.assertTrue(strip_res.get("ok"))

    def test_archive_api_operations_isolated(self) -> None:
        # Test archive creation for tar format, listing archive info,
        # and extracting all contents using temporary directories.
        with tempfile.TemporaryDirectory() as tmp_dir:
            f1 = os.path.join(tmp_dir, "file1.txt")
            with open(f1, "w", encoding="utf-8") as f:
                f.write("tar content")
            tar_path = os.path.join(tmp_dir, "archive.tar")
            c_res = self.api.archive_create(
                {"sources": [f1], "output_path": tar_path, "format": "tar"}
            )
            self.assertTrue(c_res.get("ok"))

            l_res = self.api.archive_list({"archive_path": tar_path})
            self.assertTrue(l_res.get("ok"))
            self.assertGreater(len(l_res["contents"]), 0)

            ext_dir = os.path.join(tmp_dir, "ext")
            e_res = self.api.archive_extract(
                {"archive_path": tar_path, "target_dir": ext_dir}
            )
            self.assertTrue(e_res.get("ok"))
            self.assertTrue(os.path.exists(os.path.join(ext_dir, "file1.txt")))

    def test_archive_protect_isolated(self) -> None:
        # Verify archive protect execution and error handling.
        # Ensure password enforcement and valid output creation.
        with tempfile.TemporaryDirectory() as tmp_dir:
            f1 = os.path.join(tmp_dir, "secret.txt")
            with open(f1, "w", encoding="utf-8") as f:
                f.write("confidential")

            p_res = self.api.archive_protect(
                {"source_paths": [f1], "password": "pass", "format": "zip"}
            )
            self.assertTrue(p_res.get("ok"))
            self.assertTrue(os.path.exists(p_res.get("output_path", "")))

            bad_res = self.api.archive_protect({"source_paths": [f1]})
            self.assertFalse(bad_res.get("ok"))

    def test_archive_unprotect_isolated(self) -> None:
        # Verify archive unprotect execution and error handling.
        # Ensure extraction succeeds with correct password.
        with tempfile.TemporaryDirectory() as tmp_dir:
            f1 = os.path.join(tmp_dir, "secret.txt")
            with open(f1, "w", encoding="utf-8") as f:
                f.write("confidential")

            p_res = self.api.archive_protect(
                {"source_paths": [f1], "password": "pass", "format": "zip"}
            )
            out_path = p_res.get("output_path", "")

            ext_dir = os.path.join(tmp_dir, "extracted")
            u_res = self.api.archive_unprotect(
                {"bundle_path": out_path, "password": "pass", "target_dir": ext_dir}
            )
            self.assertTrue(u_res.get("ok"))
            self.assertTrue(os.path.exists(os.path.join(ext_dir, "secret.txt")))

            bad_res = self.api.archive_unprotect({"bundle_path": out_path})
            self.assertFalse(bad_res.get("ok"))

    def test_archive_verify_integrity_isolated(self) -> None:
        # Verify bundle integrity execution and error handling.
        # Ensure password validation and hash entries are returned.
        with tempfile.TemporaryDirectory() as tmp_dir:
            f1 = os.path.join(tmp_dir, "secret.txt")
            with open(f1, "w", encoding="utf-8") as f:
                f.write("confidential")

            p_res = self.api.archive_protect(
                {"source_paths": [f1], "password": "pass", "format": "zip"}
            )
            out_path = p_res.get("output_path", "")

            v_res = self.api.archive_verify_integrity(
                {"bundle_path": out_path, "password": "pass"}
            )
            self.assertTrue(v_res.get("ok"))
            self.assertTrue(v_res.get("valid"))
            self.assertGreater(len(v_res.get("entries", [])), 0)

            bad_res = self.api.archive_verify_integrity(
                {"bundle_path": out_path, "password": "wrong"}
            )
            self.assertFalse(bad_res.get("ok"))

    def test_archive_rotate_key_isolated(self) -> None:
        # Verify bundle key rotation execution.
        # Ensure password update handles valid and invalid scenarios.
        with tempfile.TemporaryDirectory() as tmp_dir:
            f1 = os.path.join(tmp_dir, "secret.txt")
            with open(f1, "w", encoding="utf-8") as f:
                f.write("confidential")

            p_res = self.api.archive_protect(
                {"source_paths": [f1], "password": "old_pass", "format": "zip"}
            )
            out_path = p_res.get("output_path", "")
            rot_path = os.path.join(tmp_dir, "rotated.zip")

            r_res = self.api.archive_rotate_key(
                {
                    "bundle_path": out_path,
                    "old_password": "old_pass",
                    "new_password": "new_pass",
                    "output_path": rot_path,
                }
            )
            self.assertTrue(r_res.get("ok"))
            self.assertTrue(os.path.exists(rot_path))

            bad_res = self.api.archive_rotate_key(
                {
                    "bundle_path": out_path,
                    "old_password": "wrong",
                    "new_password": "new_pass",
                    "output_path": rot_path,
                }
            )
            self.assertFalse(bad_res.get("ok"))

    def test_archive_convert_isolated(self) -> None:
        # Test archive format conversion
        # and edge-case handling for unsupported formats.
        with tempfile.TemporaryDirectory() as tmp_dir:
            f1 = os.path.join(tmp_dir, "file1.txt")
            with open(f1, "w", encoding="utf-8") as f:
                f.write("content")
            tar_path = os.path.join(tmp_dir, "archive.tar")
            self.api.archive_create(
                {"sources": [f1], "output_path": tar_path, "format": "tar"}
            )

            zip_path = os.path.join(tmp_dir, "converted.zip")
            conv_res = self.api.archive_convert(
                {"archive_path": tar_path, "output_path": zip_path}
            )
            self.assertTrue(conv_res.get("ok"))
            self.assertTrue(os.path.exists(zip_path))

            bad_path = os.path.join(tmp_dir, "bad.xyz")
            bad_res = self.api.archive_convert(
                {"archive_path": tar_path, "output_path": bad_path}
            )
            self.assertFalse(bad_res.get("ok"))

    def test_archive_compare_snapshots_isolated(self) -> None:
        # Test snapshot comparison behavior for tracking changes,
        # detecting added, modified, and removed files.
        old_s = {
            "files": {
                "file1.txt": {"sha256": "hash1", "size": 10},
                "file2.txt": {"sha256": "hash2", "size": 20},
                "file3.txt": {"sha256": "hash3", "size": 30},
            }
        }
        new_s = {
            "files": {
                "file1.txt": {"sha256": "hash1", "size": 10},
                "file2.txt": {"sha256": "hash2_new", "size": 20},
                "file4.txt": {"sha256": "hash4", "size": 40},
            }
        }
        res = self.api.archive_compare_snapshots(
            {"old_snapshot": old_s, "new_snapshot": new_s}
        )
        self.assertTrue(res.get("ok"))
        self.assertIn("file4.txt", res["added"])
        self.assertIn("file2.txt", res["modified"])
        self.assertIn("file3.txt", res["removed"])
        self.assertEqual(res["total_changed"], 3)

        bad_res = self.api.archive_compare_snapshots({"old_snapshot": old_s})
        self.assertFalse(bad_res.get("ok"))

    def test_archive_snapshot_isolated(self) -> None:
        # Test archive snapshot generation and file counting
        # with optional manifest saving and missing directory error.
        with tempfile.TemporaryDirectory() as tmp_dir:
            f1 = os.path.join(tmp_dir, "file1.txt")
            with open(f1, "w", encoding="utf-8") as f:
                f.write("content")

            s_res = self.api.archive_snapshot({"directory_path": tmp_dir})
            self.assertTrue(s_res.get("ok"))
            self.assertGreater(s_res.get("file_count", 0), 0)

            manifest_path = os.path.join(tmp_dir, "manifest.json")
            sm_res = self.api.archive_snapshot(
                {"directory_path": tmp_dir, "manifest_path": manifest_path}
            )
            self.assertTrue(sm_res.get("ok"))
            self.assertTrue(os.path.exists(manifest_path))

            bad_res = self.api.archive_snapshot({})
            self.assertFalse(bad_res.get("ok"))

    def test_archive_incremental_backup_isolated(self) -> None:
        # Test creating incremental backup archive
        # and handling missing parameters error.
        with tempfile.TemporaryDirectory() as tmp_dir:
            src_dir = os.path.join(tmp_dir, "src")
            os.makedirs(src_dir)
            with open(os.path.join(src_dir, "test.txt"), "w", encoding="utf-8") as f:
                f.write("data")
            backup_dir = os.path.join(tmp_dir, "backup")
            os.makedirs(backup_dir)

            res = self.api.archive_incremental_backup(
                {
                    "directory_path": src_dir,
                    "backup_dir": backup_dir,
                }
            )
            self.assertTrue(res.get("ok"))
            self.assertIn("archive_path", res)
            self.assertTrue(os.path.exists(res["archive_path"]))

            bad_res = self.api.archive_incremental_backup({})
            self.assertFalse(bad_res.get("ok"))

    def test_archive_presets_isolated(self) -> None:
        # Verify preset loading returns a valid non-empty list
        # containing required configuration keys for each preset.
        res = self.api.archive_presets({})
        self.assertTrue(res.get("ok"))
        presets = res.get("presets", [])
        self.assertGreater(len(presets), 0)
        self.assertIn("id", presets[0])
        self.assertIn("format", presets[0])

        bad_res = self.api.archive_presets({}, invalid_kwarg=True)
        self.assertFalse(bad_res.get("ok"))

    def test_data_api_json_and_csv_operations(self) -> None:
        # Test data formatting for JSON content
        # and converting CSV data into JSON format.
        j_res = self.api.format_json({"content": '{"test":1}'})
        self.assertTrue(j_res.get("ok"))
        self.assertIn('"test": 1', j_res["result"])

        c_res = self.api.data_convert_format(
            {"content": "a,b\n1,2", "source_format": "csv", "target_format": "json"}
        )
        self.assertTrue(c_res.get("ok"))
        self.assertIn('"a": "1"', c_res["result"])

    def test_collage_presets_isolated(self) -> None:
        # Verify collage preset loading returns presets and handles
        # invalid keyword arguments smoothly via exception catch.
        res = self.api.collage_presets({})
        self.assertTrue(res.get("ok"))
        self.assertGreater(len(res.get("presets", {})), 0)

        bad_res = self.api.collage_presets({}, invalid_kwarg=True)
        self.assertFalse(bad_res.get("ok"))

    def test_encoding_api_base64_and_url(self) -> None:
        # Test encoding and decoding text using base64,
        # as well as encoding and decoding URLs.
        b64_enc = self.api.encoding_base64_encode_text({"text": "hello"})
        self.assertTrue(b64_enc.get("ok"))
        self.assertEqual(b64_enc["result"], "aGVsbG8=")

        b64_dec = self.api.encoding_base64_decode_text({"text": "aGVsbG8="})
        self.assertTrue(b64_dec.get("ok"))
        self.assertEqual(b64_dec["result"], "hello")

        url_enc = self.api.encoding_url_encode({"text": "hello world?"})
        self.assertTrue(url_enc.get("ok"))
        self.assertEqual(url_enc["result"], "hello%20world%3F")

        url_dec = self.api.encoding_url_decode({"text": "hello%20world%3F"})
        self.assertTrue(url_dec.get("ok"))
        self.assertEqual(url_dec["result"], "hello world?")


if __name__ == "__main__":
    unittest.main()
