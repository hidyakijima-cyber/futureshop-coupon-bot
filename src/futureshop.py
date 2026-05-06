"""FutureShop 操作 (Playwright)."""
import os
import re
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright, Browser, Page
from . import config
from . import gmail_client


SCREENSHOT_DIR = "screenshots"


class FutureShopClient:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser: Browser = None
        self.context = None
        self.page: Page = None

    def __enter__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
            ),
            locale="ja-JP",
        )
        self.page = self.context.new_page()
        return self

    def __exit__(self, *args):
        try:
            if self.browser:
                self.browser.close()
        finally:
            if self.playwright:
                self.playwright.stop()

    def _screenshot(self, name: str):
        """失敗時の調査用にスクショ保存."""
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        path = f"{SCREENSHOT_DIR}/{name}_{int(datetime.now().timestamp())}.png"
        try:
            self.page.screenshot(path=path, full_page=True)
            print(f"  📸 スクショ保存: {path}")
        except Exception as e:
            print(f"  スクショ失敗: {e}")

    def login(self):
        """FutureShop ログイン (2FA 自動対応)."""
        print("FutureShop ログイン開始")
        login_start = datetime.now()

        self.page.goto(f"{config.FS_BASE}/FutureShop2/Login.htm")
        self.page.fill('input[name="loginidfield"]', config.FS_STORE_KEY)
        self.page.fill('input[name="accountidfield"]', config.FS_ACCOUNT_ID)
        self.page.fill('input[name="passwordfield"]', config.FS_PASSWORD)

        with self.page.expect_navigation(wait_until="domcontentloaded"):
            self.page.click('input[type="submit"][name="submit"]')

        current_url = self.page.url
        print(f"  ログイン後URL: {current_url}")

        # 2段階認証
        if "LoginVerification" in current_url:
            print("  2段階認証検出 → Gmail から認証コード取得中...")
            code = gmail_client.get_verification_code(since=login_start)
            print(f"  認証コード取得: {code}")

            self.page.fill('input[name="verificationcodefield"]', code)
            with self.page.expect_navigation(wait_until="domcontentloaded"):
                self.page.click('input[type="submit"][name="submit"]')
            current_url = self.page.url
            print(f"  認証後URL: {current_url}")

        # 従来UI (/FutureShop2/Top.htm) と新UI (/admin/top/) の両方を許容
        if "Top.htm" not in current_url and "/admin/top" not in current_url:
            self._screenshot("login_failed")
            raise RuntimeError(f"ログイン失敗: 想定外URL {current_url}")
        print("ログイン完了 ✓")


    def create_coupon(self, *, coupon_code: str, promo_title: str,
                      publish_start: str, publish_end: str) -> None:
        """1件のクーポンを発行."""
        print(f"  クーポン発行: {coupon_code} ({promo_title})")

        # 日付組み立て
        ps_date = self._parse_date(publish_start)
        pe_date = self._parse_date(publish_end)
        now = datetime.now()
        start_time = now + timedelta(minutes=10)
        ps_full = ps_date.replace(hour=start_time.hour, minute=start_time.minute)
        pe_full = pe_date.replace(hour=23, minute=59)

        # 新規作成画面へ
        self.page.goto(f"{config.FS_BASE}/FutureShop2/NewCouponEntry.htm")
        self.page.wait_for_load_state("domcontentloaded")

        # 基本情報
        self.page.fill('input[name="couponName"]', promo_title)
        self.page.check('input[name="couponKindCode"][value="1"]')  # クローズドクーポン
        self.page.fill('input[name="couponCode"]', coupon_code)
        self.page.check('input[name="couponTargetCode"][value="0"]')  # 全員

        # 期間
        self._fill_date('releasePeriodFrom', ps_full)
        self._fill_date('releasePeriodTo', pe_full)
        self._fill_date('usePeriodFrom', ps_full)

        # クーポン期限 = 無制限
        self.page.check('input[name="couponTermUseCode"][value="00"]')
        # 利用可能枚数 = 1000枚
        self.page.check('input[name="couponUseCode"][value="1"]')
        self.page.fill('input[name="maxCouponCount"]', '1000')
        # 一人あたり = 無制限
        self.page.check('input[name="memberUseCode"][value="0"]')

        # 値引き設定
        self.page.check('input[name="discountEffectCode"][value="1"]')  # 商品値引き
        self.page.fill('input[name="totalDiscountPrice"]', '1000')
        self.page.check('input[name="targetGoodsCode"][value="0"]')  # 全商品対象

        # 利用条件 = 金額条件 3000円以上
        self.page.check('input[name="couponUseConditionCode"][value="1"]')
        self.page.fill('input[name="priceFromCondition"]', '3000')

        # 併用 = 併用可
        self.page.check('input[name="couponUseBothCode"][value="0"]')

        # 発行ボタン (image submit)
        with self.page.expect_navigation(wait_until="domcontentloaded"):
            self.page.click('input[type="image"][name="submit"]')

        if "NewCouponComplete" not in self.page.url:
            self._screenshot(f"coupon_failed_{coupon_code}")
            raise RuntimeError(f"発行失敗: 想定外URL {self.page.url}")
        print(f"  ✓ {coupon_code} 発行完了")

    def _fill_date(self, prefix: str, dt: datetime):
        self.page.fill(f'input[name="{prefix}Day"]', dt.strftime("%Y/%m/%d"))
        self.page.fill(f'input[name="{prefix}Hour"]', f"{dt.hour:02d}")
        self.page.fill(f'input[name="{prefix}Minute"]', f"{dt.minute:02d}")

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        """スプシのセル文字列を datetime に変換."""
        s = date_str.strip()
        for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S"):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
        # MM/DD 形式 → 当年で補完
        m = re.match(r"^(\d{1,2})[/-](\d{1,2})$", s)
        if m:
            return datetime(datetime.now().year, int(m.group(1)), int(m.group(2)))
        raise ValueError(f"日付形式不明: {s}")
