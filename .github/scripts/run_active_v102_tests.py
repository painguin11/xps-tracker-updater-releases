from pathlib import Path
import subprocess
import sys

TESTS = [
    'working_source/tests/regression_post_v100_826_trouble_geometry.py',
    'working_source/tests/regression_post_v100_trouble_cells.py',
    'working_source/tests/regression_trouble_workbook.py',
    'working_source/tests/regression_post_v99_faint_vertical_grid.py',
    'working_source/tests/regression_post_v98_short_wide_compact_table.py',
    'working_source/tests/regression_post_v97_cleaning_clipped_digits.py',
    'working_source/tests/regression_post_v96_msa_editable_fields.py',
    'working_source/tests/regression_post_v95_new_packet_ocr.py',
    'working_source/tests/regression_post_v95_padded_endpoint_ids.py',
    'working_source/tests/regression_post_v95_msa_suffix_review.py',
    'working_source/tests/regression_v95_faint_compact_rows.py',
    'working_source/tests/regression_v95_exact_endpoint_priority.py',
    'working_source/tests/regression_v94_stacked_endpoint_digits.py',
    'working_source/tests/regression_v93_workorder_low_confidence_blank.py',
    'working_source/tests/regression_v93_new_asset_notes.py',
    'working_source/tests/regression_v92_workorder_4_or_5_digits.py',
    'working_source/tests/regression_v91_workorder_color_ocr.py',
    'working_source/tests/regression_v91_new_asset_preview_and_endpoint_recovery.py',
    'working_source/tests/regression_v90_review_ui.py',
    'working_source/tests/regression_v89_review_workflow.py',
    'working_source/tests/regression_v89_printed_pair_identity.py',
    'working_source/tests/regression_v89_manhole_count_and_final_total.py',
    'working_source/tests/regression_v88_continuations.py',
    'working_source/tests/regression_v87_total_summary_separator.py',
    'working_source/tests/regression_v86_assets_and_edit.py',
    'working_source/tests/regression_v85_edit_row_previews.py',
    'working_source/tests/regression_v85_mandatory_rows_and_length_votes.py',
    'working_source/tests/regression_v84_real_packet_length_logic.py',
    'working_source/tests/regression_v83_length_recovery.py',
    'working_source/tests/regression_v83_exact_pdf_numbers.py',
    'working_source/tests/regression_v83_total_preview_group_errors.py',
    'working_source/tests/regression_v82_pair_video_lengths.py',
    'working_source/tests/regression_v82_master_asset_format.py',
    'working_source/tests/regression_v82_suffix_guard.py',
    'working_source/tests/regression_v82_cleaning_header_noise.py',
    'working_source/tests/regression_v82_layout_threshold.py',
    'working_source/tests/regression_v81_header_outline.py',
    'working_source/tests/regression_v80_ocr_total_ui.py',
    'working_source/tests/regression_v79_layout_speed.py',
    'working_source/tests/regression_v78_rollback.py',
    'working_source/tests/regression_v75_811_ocr.py',
    'working_source/tests/regression_v74_row_filtering.py',
    'working_source/tests/regression_v73_total_dates.py',
    'working_source/tests/regression_compact_table_fallback.py',
    'working_source/tests/regression_length_totals.py',
    'working_source/tests/regression_split_pipes.py',
    'working_source/tests/regression_new_assets.py',
    'working_source/tests/regression_master_insert.py',
    'working_source/tests/regression_r2_endpoint_ocr.py',
    'working_source/tests/regression_v102_discard_work_orders.py',
]

for test in TESTS:
    if not Path(test).exists():
        raise SystemExit(f'Missing active regression: {test}')
    print(f'===== {test} =====', flush=True)
    subprocess.run([sys.executable, test], check=True)
print(f'PASS: {len(TESTS)} active regression scripts')
