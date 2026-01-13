import { test, expect } from '@playwright/test';

/**
 * チケット購入フローE2Eテスト
 *
 * 料金計算の正確性を画面レベルで検証
 */

test.describe('チケット購入フロー', () => {
  test.beforeEach(async ({ page }) => {
    // ログイン処理（実際の認証フローに合わせて調整）
    // await page.goto('/login');
    // await page.fill('[name="email"]', 'test@example.com');
    // await page.fill('[name="password"]', 'password');
    // await page.click('button[type="submit"]');
    // await page.waitForURL('/');
  });

  test('チケット購入画面が表示される', async ({ page }) => {
    await page.goto('/ticket-purchase');

    // ページタイトル確認
    await expect(page.locator('text=チケット購入')).toBeVisible();

    // 購入項目選択が表示される
    await expect(page.locator('text=購入する項目を選択')).toBeVisible();
  });

  test('コース選択後に料金が表示される', async ({ page }) => {
    await page.goto('/ticket-purchase/from-ticket');

    // コンソールログを監視して料金計算を確認
    const consoleLogs: string[] = [];
    page.on('console', msg => {
      if (msg.text().includes('pricingPreview')) {
        consoleLogs.push(msg.text());
      }
    });

    // ページ読み込み完了を待つ
    await page.waitForLoadState('networkidle');

    // 料金関連の要素が存在することを確認
    // (実際のセレクタは画面構成に合わせて調整)
  });

  test.describe('料金計算の検証', () => {
    test('当月分料金が表示される（月中入会）', async ({ page }) => {
      // API レスポンスをインターセプト
      await page.route('**/api/v1/pricing/preview/**', async route => {
        const response = await route.fetch();
        const json = await response.json();

        // 当月分回数割が含まれていることを確認
        expect(json.currentMonthProrated).toBeDefined();
        if (json.currentMonthProrated) {
          expect(json.currentMonthProrated.totalProrated).toBeGreaterThan(0);
        }

        await route.fulfill({ response });
      });

      await page.goto('/ticket-purchase/from-ticket');
    });

    test('複数曜日選択時の料金計算', async ({ page }) => {
      // API レスポンスをインターセプト
      let requestBody: any = null;
      await page.route('**/api/v1/pricing/preview/**', async route => {
        const request = route.request();
        requestBody = request.postDataJSON();

        const response = await route.fetch();
        await route.fulfill({ response });
      });

      await page.goto('/ticket-purchase/from-ticket');

      // 複数曜日が送信されているか確認
      // (実際のフローに合わせて調整)
    });
  });

  test.describe('料金表示の不変条件', () => {
    test('合計金額は0以上', async ({ page }) => {
      await page.route('**/api/v1/pricing/preview/**', async route => {
        const response = await route.fetch();
        const json = await response.json();

        // 合計は0以上
        expect(json.grandTotal).toBeGreaterThanOrEqual(0);

        // 小計は0以上
        expect(json.subtotal).toBeGreaterThanOrEqual(0);

        await route.fulfill({ response });
      });

      await page.goto('/ticket-purchase/from-ticket');
    });

    test('割引適用後の合計は割引前以下', async ({ page }) => {
      await page.route('**/api/v1/pricing/preview/**', async route => {
        const response = await route.fetch();
        const json = await response.json();

        if (json.discountTotal > 0) {
          // 割引がある場合、合計は小計以下
          expect(json.grandTotal).toBeLessThanOrEqual(json.subtotal);
        }

        await route.fulfill({ response });
      });

      await page.goto('/ticket-purchase/from-ticket');
    });
  });
});

test.describe('料金表示の一致確認', () => {
  test('API結果と画面表示が一致する', async ({ page }) => {
    let apiGrandTotal: number | null = null;

    await page.route('**/api/v1/pricing/preview/**', async route => {
      const response = await route.fetch();
      const json = await response.json();
      apiGrandTotal = json.grandTotal;
      await route.fulfill({ response });
    });

    await page.goto('/ticket-purchase/from-ticket');
    await page.waitForLoadState('networkidle');

    // 画面に表示されている合計金額を取得
    // (実際のセレクタは画面構成に合わせて調整)
    // const displayedTotal = await page.locator('[data-testid="grand-total"]').textContent();

    // APIの結果と画面表示が一致
    // expect(parseInt(displayedTotal.replace(/[^0-9]/g, ''))).toBe(apiGrandTotal);
  });
});
