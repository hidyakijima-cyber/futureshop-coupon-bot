"""設定値・環境変数の読み込み."""
import os

# ===== スプシ =====
SPREADSHEET_ID = os.environ.get(
    "SPREADSHEET_ID",
    "1iFutRWelgb7nv-mtSp_tFV_uHfxE1e7ORs7X4yyBU7g",
)
SHEET_NAME = "クーポン管理"
HEADER_ROW = 1

# 列マッピング (1-indexed)
COL_PUBLISH_START = 8   # H列
COL_PUBLISH_END = 9     # I列
COL_COUPON_CODE = 11    # K列
COL_PROMO_TITLE = 14    # N列
COL_ISSUE_STATUS = 15   # O列
COL_ISSUED_FLAG = 21    # U列

# フィルタ
FILTER_COLUMN = "E"
FILTER_VALUE = "3000円以上の全商品1000円OFFクーポン"

# ===== FutureShop =====
FS_BASE = "https://hidya.admin.future-shop.net"
FS_STORE_KEY = os.environ["FS_STORE_KEY"]
FS_ACCOUNT_ID = os.environ["FS_ACCOUNT_ID"]
FS_PASSWORD = os.environ["FS_PASSWORD"]

# ===== Gmail =====
GMAIL_CLIENT_ID = os.environ["GMAIL_CLIENT_ID"]
GMAIL_CLIENT_SECRET = os.environ["GMAIL_CLIENT_SECRET"]
GMAIL_REFRESH_TOKEN = os.environ["GMAIL_REFRESH_TOKEN"]
GMAIL_VERIFICATION_FROM = "system@admin.future-shop.net"

# ===== GCP サービスアカウント (JSON 文字列) =====
GCP_SA_KEY_JSON = os.environ["GCP_SA_KEY"]

# ===== 実行情報 =====
TRIGGERED_BY = os.environ.get("TRIGGERED_BY", "manual")
