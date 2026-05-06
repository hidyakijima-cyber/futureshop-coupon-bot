"""エントリポイント."""
import sys
from . import config
from . import sheet_client
from .futureshop import FutureShopClient


def main() -> int:
    print(f"=== FutureShop クーポン発行 開始 ===")
    print(f"トリガー: {config.TRIGGERED_BY}")

    # 対象行取得
    targets = sheet_client.get_target_rows()
    print(f"対象件数: {len(targets)}件")
    if not targets:
        print("処理対象なし。終了します。")
        return 0

    success = 0
    fail = 0
    errors = []

    with FutureShopClient(headless=True) as fs:
        try:
            fs.login()
        except Exception as e:
            print(f"❌ ログイン失敗: {e}")
            return 1

        for t in targets:
            if not t["coupon_code"] or not t["promo_title"]:
                fail += 1
                errors.append(f"行{t['row_num']}: 必須項目欠落")
                continue
            try:
                fs.create_coupon(
                    coupon_code=t["coupon_code"],
                    promo_title=t["promo_title"],
                    publish_start=t["publish_start"],
                    publish_end=t["publish_end"],
                )
                sheet_client.mark_issued(t["row_num"])
                success += 1
            except Exception as e:
                fail += 1
                errors.append(f"行{t['row_num']} ({t['coupon_code']}): {e}")
                print(f"  ❌ {t['coupon_code']} 失敗: {e}")

    print(f"\n=== 完了 ===")
    print(f"成功: {success}件 / 失敗: {fail}件")
    if errors:
        print("エラー詳細:")
        for e in errors:
            print(f"  - {e}")
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
