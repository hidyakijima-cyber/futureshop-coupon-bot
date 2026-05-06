"""Gmail API で 2FA 認証コードを取得."""
import re
import time
from datetime import datetime, timedelta, timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from . import config


def _get_gmail_service():
    """リフレッシュトークンから Gmail API サービスを初期化."""
    creds = Credentials(
        token=None,
        refresh_token=config.GMAIL_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=config.GMAIL_CLIENT_ID,
        client_secret=config.GMAIL_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )
    creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)


def get_verification_code(since: datetime, timeout_seconds: int = 90, poll_interval: int = 3) -> str:
    """指定時刻以降に届いた認証コードメールを取得して6桁コードを返す."""
    service = _get_gmail_service()
    # クロックずれ吸収のため 30秒前から検索
    since_ts = int((since - timedelta(seconds=30)).timestamp())
    query = f"from:{config.GMAIL_VERIFICATION_FROM} subject:認証コード after:{since_ts}"

    deadline = time.time() + timeout_seconds
    elapsed = 0
    while time.time() < deadline:
        time.sleep(poll_interval)
        elapsed += poll_interval

        result = service.users().messages().list(
            userId="me", q=query, maxResults=5,
        ).execute()

        messages = result.get("messages", [])
        if not messages:
            print(f"  [Gmail] 認証コード待機中... ({elapsed}秒経過)")
            continue

        # 最新メッセージから抽出
        msg_id = messages[0]["id"]
        msg = service.users().messages().get(
            userId="me", id=msg_id, format="metadata",
            metadataHeaders=["Subject", "Date"],
        ).execute()

        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        subject = headers.get("Subject", "")
        match = re.search(r"認証コード[:：]\s*(\d+)", subject)
        if match:
            return match.group(1)

    raise TimeoutError(f"{timeout_seconds}秒以内に認証コードメールを取得できませんでした")
