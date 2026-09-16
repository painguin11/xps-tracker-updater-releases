from pathlib import Path
import subprocess
import sys

TESTS=[
    'regression_post_v103_manhole_reordered_columns.py',
    'regression_post_v102_manhole_expected_count_retry.py',
    'regression_post_v102_manhole_partial_tokens.py',
    'regression_post_v100_826_trouble_geometry.py',
    'regression_post_v100_trouble_cells.py',
    'regression_trouble_workbook.py',
    'regression_post_v99_faint_vertical_grid.py',
    'regression_post_v98_short_wide_compact_table.py',
    'regression_post_v97_cleaning_clipped_digits.py',
    'regression_post_v96_msa_editable_fields.py',
    'regression_post_v95_new_packet_ocr.py',
    'regression_post_v95_padded_endpoint_ids.py',
    'regression_post_v95_msa_suffix_review.py',
    'regression_v95_faint_compact_rows.py',
    'regression_v95_exact_endpoint_priority.py',
    'regression_v94_stacked_endpoint_digits.py',
    'regression_v93_workorder_low_confidence_blank.py',
    'regression_v93_new_asset_notes.py',
    'regression_v92_workorder_4_or_5_digits.py',
    'regression_v91_workorder_color_ocr.py',
    'regression_v91_new_asset_preview_and_endpoint_recovery.py',
    'regression_v90_review_ui.py',
    'regression_v89_review_workflow.py',
    'regression_v89_printed_pair_identity.py',
    'regression_v89_manhole_count_and_final_total.py',
    'regression_v88_continuations.py',
    'regression_v87_total_summary_separator.py',
    'regression_v86_assets_and_edit.py',
    'regression_v85_edit_row_previews.py',
    'regression_v85_mandatory_rows_and_length_votes.py',
    'regression_v84_real_packet_length_logic.py',
    'regression_v83_length_recovery.py',
    'regression_v83_exact_pdf_numbers.py',
    'regression_v83_total_preview_group_errors.py',
    'regression_v82_pair_video_lengths.py',
    'regression_v82_master_asset_format.py',
    'regression_v82_suffix_guard.py',
    'regression_v82_cleaning_header_noise.py',
    'regression_v82_layout_threshold.py',
    'regression_v81_header_outline.py',
    'regression_v80_ocr_total_ui.py',
    'regression_v79_layout_speed.py',
    'regression_v78_rollback.py',
    'regression_v75_811_ocr.py',
    'regression_v74_row_filtering.py',
    'regression_v73_total_dates.py',
    'regression_compact_table_fallback.py',
    'regression_length_totals.py',
    'regression_split_pipes.py',
    'regression_new_assets.py',
    'regression_master_insert.py',
    'regression_r2_endpoint_ocr.py',
    'regression_v102_review_wrapper.py',
]
root=Path(__file__).resolve().parents[1]/'tests'
for name in TESTS:
    path=root/name
    if not path.exists():
        raise SystemExit(f'Missing active regression: {path}')
    print(f'===== {path} =====',flush=True)
    subprocess.run([sys.executable,str(path)],check=True)
print(f'FULL ACTIVE REGRESSION SUITE: {len(TESTS)}/{len(TESTS)} passed')
