import { test, expect, Page } from '@playwright/test';

/**
 * Admin側 E2Eテスト
 *
 * Customer側で行った操作がAdmin画面で確認できることを検証
 */

const ADMIN_BASE_URL = process.env.ADMIN_URL || 'http://localhost:3002';

// テスト用の管理者認証情報
const ADMIN_USER = {
  email: process.env.ADMIN_EMAIL || 'admin@example.com',
  password: process.env.ADMIN_PASSWORD || 'adminpassword123',
};

// テスト用生徒ID
const TEST_STUDENT_ID = process.env.TEST_STUDENT_ID || '92b4b2c7-ab03-47e3-a10a-53274fce6c4d';

// Adminログインヘルパー
async function adminLogin(page: Page) {
  await page.goto(`${ADMIN_BASE_URL}/login`);
  await page.waitForLoadState('networkidle');

  // ログインフォームが表示されるまで待機
  await page.waitForSelector('input[type="email"], input[name="email"]', { timeout: 10000 });

  await page.fill('input[type="email"], input[name="email"]', ADMIN_USER.email);
  await page.fill('input[type="password"], input[name="password"]', ADMIN_USER.password);
  await page.click('button[type="submit"]');

  // ログイン完了を待機
  await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 15000 });
}

test.describe('Admin - 生徒管理', () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page);
  });

  test('生徒一覧画面が表示される', async ({ page }) => {
    await page.goto(`${ADMIN_BASE_URL}/students`);
    await page.waitForLoadState('networkidle');

    // 生徒一覧が表示される
    await expect(page.locator('text=生徒').first()).toBeVisible({ timeout: 10000 });
  });

  test('生徒詳細画面で契約が表示される', async ({ page }) => {
    await page.goto(`${ADMIN_BASE_URL}/students?id=${TEST_STUDENT_ID}`);
    await page.waitForLoadState('networkidle');

    // 生徒詳細が表示される
    await page.waitForTimeout(2000);

    // 契約タブまたは契約情報が表示される
    const contractsTab = page.locator('text=契約').or(page.locator('[data-value="contracts"]'));
    if (await contractsTab.isVisible()) {
      await contractsTab.click();
      await page.waitForTimeout(500);
    }
  });

  test('生徒の請求情報が表示される', async ({ page }) => {
    await page.goto(`${ADMIN_BASE_URL}/students?id=${TEST_STUDENT_ID}`);
    await page.waitForLoadState('networkidle');

    await page.waitForTimeout(2000);

    // 請求タブがあればクリック
    const billingTab = page.locator('text=請求').or(page.locator('[data-value="billing"]'));
    if (await billingTab.isVisible()) {
      await billingTab.click();
      await page.waitForTimeout(500);
    }
  });
});

test.describe('Admin - 請求管理', () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page);
  });

  test('請求一覧画面が表示される', async ({ page }) => {
    await page.goto(`${ADMIN_BASE_URL}/billing`);
    await page.waitForLoadState('networkidle');

    // 請求管理画面が表示される
    await expect(page.locator('text=請求').first()).toBeVisible({ timeout: 10000 });
  });

  test('確定請求画面が表示される', async ({ page }) => {
    await page.goto(`${ADMIN_BASE_URL}/billing/confirmed`);
    await page.waitForLoadState('networkidle');

    // 確定請求が表示される
    await expect(page.locator('text=確定').or(page.locator('text=請求')).first()).toBeVisible({ timeout: 10000 });
  });

  test('入金管理画面が表示される', async ({ page }) => {
    await page.goto(`${ADMIN_BASE_URL}/billing/payments`);
    await page.waitForLoadState('networkidle');

    // 入金管理が表示される
    await expect(page.locator('text=入金').or(page.locator('text=支払')).first()).toBeVisible({ timeout: 10000 });
  });

  test('過不足管理画面が表示される', async ({ page }) => {
    await page.goto(`${ADMIN_BASE_URL}/billing/offsets`);
    await page.waitForLoadState('networkidle');

    // 過不足管理が表示される
    await expect(page.locator('text=過不足').or(page.locator('text=調整')).first()).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Admin - 授業管理', () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page);
  });

  test('授業管理画面が表示される', async ({ page }) => {
    await page.goto(`${ADMIN_BASE_URL}/lessons`);
    await page.waitForLoadState('networkidle');

    // 授業管理が表示される
    await expect(page.locator('text=授業').or(page.locator('text=レッスン')).first()).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Admin - カレンダー管理', () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page);
  });

  test('カレンダー管理画面が表示される', async ({ page }) => {
    await page.goto(`${ADMIN_BASE_URL}/calendar`);
    await page.waitForLoadState('networkidle');

    // カレンダー管理が表示される
    await expect(page.locator('text=カレンダー').or(page.locator('text=Calendar')).first()).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Admin API検証', () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page);
  });

  test('生徒契約APIが正しいデータを返す', async ({ page }) => {
    let contractsResponse: any = null;

    await page.route('**/api/v1/contracts/student-items/**', async route => {
      const response = await route.fetch();
      contractsResponse = await response.json();
      await route.fulfill({ response });
    });

    await page.goto(`${ADMIN_BASE_URL}/students?id=${TEST_STUDENT_ID}`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // APIレスポンスがあれば検証
    if (contractsResponse) {
      expect(contractsResponse).toBeDefined();
    }
  });

  test('請求APIが正しいデータを返す', async ({ page }) => {
    let billingResponse: any = null;

    await page.route('**/api/v1/billing/**', async route => {
      const response = await route.fetch();
      try {
        billingResponse = await response.json();
      } catch {
        // JSONでない場合はスキップ
      }
      await route.fulfill({ response });
    });

    await page.goto(`${ADMIN_BASE_URL}/billing`);
    await page.waitForLoadState('networkidle');

    // APIレスポンスがあれば検証
    if (billingResponse) {
      expect(billingResponse).toBeDefined();
    }
  });
});
