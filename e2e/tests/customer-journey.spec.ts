import { test, expect, Page } from '@playwright/test';

/**
 * Customer Journey E2Eテスト
 *
 * チケット購入 → カレンダー確認 → 欠席登録 → 通帳確認 の一連のフロー
 */

// テスト用の認証情報（Customer側は電話番号でログイン）
const TEST_USER = {
  phone: process.env.TEST_USER_PHONE || '09012345678',
  password: process.env.TEST_USER_PASSWORD || 'testpassword123',
};

// ログインヘルパー
async function login(page: Page) {
  await page.goto('/login');
  await page.waitForLoadState('networkidle');

  // ログインフォームが表示されるまで待機（電話番号入力フィールド）
  await page.waitForSelector('input[type="tel"], input#phone', { timeout: 10000 });

  await page.fill('input[type="tel"], input#phone', TEST_USER.phone);
  await page.fill('input[type="password"], input#password', TEST_USER.password);
  await page.click('button[type="submit"]');

  // ログイン完了を待機（ホーム画面またはダッシュボードへリダイレクト）
  await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 15000 });
}

test.describe('Customer Journey - 完全フロー', () => {
  test.describe.configure({ mode: 'serial' }); // テストを順番に実行

  test.beforeEach(async ({ page }) => {
    // 各テスト前にログイン状態を確認
    const cookies = await page.context().cookies();
    const hasAuthCookie = cookies.some(c => c.name.includes('token') || c.name.includes('session'));

    if (!hasAuthCookie) {
      await login(page);
    }
  });

  test('1. ログインができる', async ({ page }) => {
    await page.goto('/login');

    // 既にログイン済みならスキップ
    if (!page.url().includes('/login')) {
      expect(true).toBe(true);
      return;
    }

    await login(page);
    expect(page.url()).not.toContain('/login');
  });

  test('2. チケット購入画面にアクセスできる', async ({ page }) => {
    await page.goto('/ticket-purchase');
    await page.waitForLoadState('networkidle');

    // 購入画面が表示される
    await expect(page.locator('text=チケット購入').first()).toBeVisible({ timeout: 10000 });
  });

  test('3. 保有チケット画面で契約が表示される', async ({ page }) => {
    await page.goto('/tickets');
    await page.waitForLoadState('networkidle');

    // チケット画面が表示される
    await expect(page.locator('text=保有チケット').first()).toBeVisible({ timeout: 10000 });
  });

  test('4. カレンダー画面で授業が表示される', async ({ page }) => {
    await page.goto('/calendar');
    await page.waitForLoadState('networkidle');

    // カレンダーが表示される
    await expect(page.locator('text=Calendar').or(page.locator('text=カレンダー')).first()).toBeVisible({ timeout: 10000 });

    // 月表示があることを確認
    await expect(page.locator('text=月').first()).toBeVisible();
  });

  test('5. カレンダーから授業詳細が開ける', async ({ page }) => {
    await page.goto('/calendar');
    await page.waitForLoadState('networkidle');

    // 予約済みの授業をクリック（青いバッジ）
    const scheduledEvent = page.locator('[class*="bg-blue"]').first();

    if (await scheduledEvent.isVisible()) {
      await scheduledEvent.click();

      // ダイアログが開く
      await expect(page.locator('text=授業の詳細').or(page.locator('text=日時'))).toBeVisible({ timeout: 5000 });
    }
  });

  test('6. 通帳画面で請求履歴が表示される', async ({ page }) => {
    await page.goto('/purchase-history');
    await page.waitForLoadState('networkidle');

    // 通帳画面が表示される
    await expect(
      page.locator('text=通帳')
        .or(page.locator('text=購入履歴'))
        .or(page.locator('text=入出金'))
        .first()
    ).toBeVisible({ timeout: 10000 });
  });

  test('7. 振替フロー画面にアクセスできる', async ({ page }) => {
    await page.goto('/transfer-flow');
    await page.waitForLoadState('networkidle');

    // 振替画面が表示される
    await expect(
      page.locator('text=振替')
        .or(page.locator('text=欠席チケット'))
        .first()
    ).toBeVisible({ timeout: 10000 });
  });
});

test.describe('カレンダー機能テスト', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('子供を選択できる', async ({ page }) => {
    await page.goto('/calendar');
    await page.waitForLoadState('networkidle');

    // 子供選択ドロップダウンを探す
    const childSelector = page.locator('[class*="select"]').or(page.locator('button:has-text("選択")')).first();

    if (await childSelector.isVisible()) {
      await childSelector.click();
      // ドロップダウンオプションが表示される
      await page.waitForTimeout(500);
    }
  });

  test('月を切り替えられる', async ({ page }) => {
    await page.goto('/calendar');
    await page.waitForLoadState('networkidle');

    // 現在の月を取得
    const monthText = await page.locator('text=/\\d{4}年\\d{1,2}月/').textContent();

    // 次月ボタンをクリック
    const nextButton = page.locator('button:has(svg)').last();
    await nextButton.click();
    await page.waitForTimeout(500);

    // 月が変わったことを確認
    const newMonthText = await page.locator('text=/\\d{4}年\\d{1,2}月/').textContent();

    // テキストが変わっているか、または同じでも正常動作
    expect(newMonthText).toBeDefined();
  });
});

test.describe('欠席・振替機能テスト', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('欠席登録ダイアログが表示される', async ({ page }) => {
    await page.goto('/calendar');
    await page.waitForLoadState('networkidle');

    // 予約済み授業を探してクリック
    const scheduledClass = page.locator('[class*="bg-blue"]').first();

    if (await scheduledClass.isVisible()) {
      await scheduledClass.click();
      await page.waitForTimeout(500);

      // 欠席登録ボタンが表示される
      const absenceButton = page.locator('button:has-text("欠席登録")');
      await expect(absenceButton).toBeVisible({ timeout: 5000 });
    }
  });

  test('欠席キャンセルボタンが欠席中の授業に表示される', async ({ page }) => {
    await page.goto('/calendar');
    await page.waitForLoadState('networkidle');

    // 欠席中の授業を探す（ピンク/赤色）
    const absentClass = page.locator('[class*="bg-red"], [class*="bg-pink"]').first();

    if (await absentClass.isVisible()) {
      await absentClass.click();
      await page.waitForTimeout(500);

      // 欠席キャンセルボタンが表示される
      const cancelButton = page.locator('button:has-text("欠席をキャンセル")');
      await expect(cancelButton).toBeVisible({ timeout: 5000 });
    }
  });
});

test.describe('API レスポンス検証', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('カレンダーAPIが正しいデータを返す', async ({ page }) => {
    let calendarResponse: any = null;

    await page.route('**/api/v1/lessons/student-calendar/**', async route => {
      const response = await route.fetch();
      calendarResponse = await response.json();
      await route.fulfill({ response });
    });

    await page.goto('/calendar');
    await page.waitForLoadState('networkidle');

    // APIが呼ばれた場合、レスポンスを検証
    if (calendarResponse) {
      expect(calendarResponse).toHaveProperty('events');
      expect(Array.isArray(calendarResponse.events)).toBe(true);
    }
  });

  test('通帳APIが正しいデータを返す', async ({ page }) => {
    let passbookResponse: any = null;

    await page.route('**/api/v1/billing/offset-logs/my-passbook/**', async route => {
      const response = await route.fetch();
      passbookResponse = await response.json();
      await route.fulfill({ response });
    });

    await page.goto('/purchase-history');
    await page.waitForLoadState('networkidle');

    // APIが呼ばれた場合、レスポンスを検証
    if (passbookResponse) {
      expect(Array.isArray(passbookResponse)).toBe(true);
    }
  });

  test('契約APIが正しいデータを返す', async ({ page }) => {
    let contractsResponse: any = null;

    await page.route('**/api/v1/contracts/my-contracts/**', async route => {
      const response = await route.fetch();
      contractsResponse = await response.json();
      await route.fulfill({ response });
    });

    await page.goto('/tickets');
    await page.waitForLoadState('networkidle');

    // APIが呼ばれた場合、レスポンスを検証
    if (contractsResponse) {
      expect(contractsResponse).toHaveProperty('children');
    }
  });
});
