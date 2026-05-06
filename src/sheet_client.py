"""Google Spreadsheet 操作 (gspread)."""
import json
import gspread
from google.oauth2 import service_account
from . import config


def _get_worksheet():
    creds_dict = json.loads(config.GCP_SA_KEY_JSON)
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(config.SPREADSHEET_ID)
    return sh.worksheet(config.SHEET_NAME)


def _filter_col_index() -> int:
    """フィルタ列レター(E等)を 0-indexed に変換."""
    return ord(config.FILTER_COLUMN.upper()) - ord("A")


def get_target_rows() -> list[dict]:
    """フィルタ条件にマッチする行をリストで返す."""
    ws = _get_worksheet()
    all_values = ws.get_all_values()
    if len(all_values) <= config.HEADER_ROW:
        return []

    targets = []
    fc = _filter_col_index()

    for i, row in enumerate(all_values[config.HEADER_ROW:], start=config.HEADER_ROW + 1):
        # 安全に列アクセス
        def cell(idx_1based):
            i0 = idx_1based - 1
            return row[i0] if i0 < len(row) else ""

        filter_val = (row[fc] if fc < len(row) else "").strip()
        if filter_val != config.FILTER_VALUE:
            continue

        issued_flag = cell(config.COL_ISSUED_FLAG).strip().upper()
        # 空欄/FALSE/0 のみ処理対象。TRUE(発行済み)やERROR(エラー)は対象外
        if issued_flag not in ("", "FALSE", "0"):
            continue


        targets.append({
            "row_num": i,
            "coupon_code": cell(config.COL_COUPON_CODE).strip(),
            "promo_title": cell(config.COL_PROMO_TITLE).strip(),
            "publish_start": cell(config.COL_PUBLISH_START).strip(),
            "publish_end": cell(config.COL_PUBLISH_END).strip(),
        })

    return targets


def mark_issued(row_num: int):
    """成功時の書き戻し: U列=TRUE, O列=発行済み."""
    ws = _get_worksheet()
    ws.update_cell(row_num, config.COL_ISSUED_FLAG, "TRUE")
    ws.update_cell(row_num, config.COL_ISSUE_STATUS, "発行済み")


def mark_error(row_num: int, error_message: str):
    """失敗時の書き戻し: U列=ERROR, O列=エラーメッセージ.
    実行者がスプシで失敗理由を確認できるようにする.
    """
    ws = _get_worksheet()
    ws.update_cell(row_num, config.COL_ISSUED_FLAG, "ERROR")
    msg = f"❌ {error_message[:200]}"
    ws.update_cell(row_num, config.COL_ISSUE_STATUS, msg)


def mark_unissued(row_num: int):
    """過去日エラー時の書き戻し: U列は触らず, O列="未発行".
    日付を修正して再実行すれば再度処理対象になる.
    """
    ws = _get_worksheet()
    ws.update_cell(row_num, config.COL_ISSUE_STATUS, "未発行")

