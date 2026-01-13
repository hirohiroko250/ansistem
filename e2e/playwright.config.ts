import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: false, // 順番に実行
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1, // シングルワーカーで実行
  timeout: 60000, // 60秒タイムアウト
  reporter: [
    ['html', { open: 'never' }],
    ['json', { outputFile: 'test-results.json' }],
    ['list'], // コンソール出力
  ],
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    // 認証状態を保持
    storageState: undefined,
  },

  projects: [
    {
      name: 'customer-chromium',
      testMatch: ['**/customer-journey.spec.ts', '**/ticket-purchase.spec.ts'],
      use: {
        ...devices['Desktop Chrome'],
        baseURL: 'http://localhost:3000',
      },
    },
    {
      name: 'admin-chromium',
      testMatch: '**/admin-verification.spec.ts',
      use: {
        ...devices['Desktop Chrome'],
        baseURL: 'http://localhost:3002',
      },
    },
    {
      name: 'customer-mobile',
      testMatch: '**/customer-journey.spec.ts',
      use: {
        ...devices['iPhone 13'],
        baseURL: 'http://localhost:3000',
      },
    },
  ],

  // ローカル開発時のサーバー起動設定
  webServer: process.env.CI ? undefined : [
    {
      command: 'cd ../frontend/customer && npm run dev',
      url: 'http://localhost:3000',
      reuseExistingServer: true,
      timeout: 120000,
    },
    {
      command: 'cd ../frontend/admin && npm run dev',
      url: 'http://localhost:3002',
      reuseExistingServer: true,
      timeout: 120000,
    },
  ],
});
