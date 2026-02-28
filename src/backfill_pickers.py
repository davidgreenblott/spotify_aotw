#!/usr/bin/env python3
"""One-off script: fill the 'picker' column for all existing sheet rows.

Assigns initials cyclically (SS → DG → RB → JC) based on pick number.
Only writes to rows where the picker cell is currently empty.

Usage:
    python src/backfill_pickers.py [--dry-run] [--force]
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import gspread
from add_album import get_google_sheet, get_header_row_and_map
from logging_config import setup_logging

logger = setup_logging()

_FIRST_CYCLE = ['SS', 'DG', 'RB']        # Jack skipped first time round
_FULL_CYCLE  = ['SS', 'DG', 'RB', 'JC']


def _picker_for(pick_number: int) -> str:
    """Return the initials for a given pick number following the cycle rule."""
    if pick_number <= len(_FIRST_CYCLE):
        return _FIRST_CYCLE[pick_number - 1]
    pos = (pick_number - 1 - len(_FIRST_CYCLE)) % len(_FULL_CYCLE)
    return _FULL_CYCLE[pos]


def backfill_pickers(sheet_id=None, sheet_tab=None, creds_path=None, dry_run=False, force=False):
    worksheet = get_google_sheet(sheet_id, sheet_tab, creds_path)
    header_row, header_map = get_header_row_and_map(worksheet)

    picker_col_idx = header_map.get('picker')
    pick_col_idx = header_map.get('pick')

    if picker_col_idx is None:
        raise ValueError("No 'picker' column found in sheet header.")
    if pick_col_idx is None:
        raise ValueError("No 'pick' column found in sheet header.")

    all_values = worksheet.get_all_values()
    data_rows = all_values[header_row:]

    updates = []
    for i, row in enumerate(data_rows):
        if not row or not any(cell.strip() for cell in row):
            continue

        current_picker = row[picker_col_idx].strip() if picker_col_idx < len(row) else ''
        if current_picker and not force:
            continue  # already assigned — don't overwrite

        try:
            pick_num = int(float(row[pick_col_idx].strip())) if pick_col_idx < len(row) else 0
        except (ValueError, TypeError):
            pick_num = 0

        if pick_num <= 0:
            continue

        initials = _picker_for(pick_num)
        sheet_row = header_row + 1 + i  # gspread is 1-indexed
        cell_addr = gspread.utils.rowcol_to_a1(sheet_row, picker_col_idx + 1)
        updates.append({'range': cell_addr, 'values': [[initials]]})
        logger.info('pick #%d (row %d) → %s', pick_num, sheet_row, initials)

    if not updates:
        logger.info('Nothing to update.')
        return

    logger.info('%d rows to update.', len(updates))
    if dry_run:
        logger.info('Dry run — no changes written.')
    else:
        worksheet.batch_update(updates)
        logger.info('Done.')


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    force = '--force' in sys.argv
    backfill_pickers(dry_run=dry_run, force=force)
