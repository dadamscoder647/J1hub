import { test, expect } from '@playwright/test';

test('worker journey: register -> verify -> apply', async ({ page }) => {
  await page.route('**/auth/register', async (route) => route.fulfill({ status: 201, body: JSON.stringify({}) }));
  await page.route('**/auth/login', async (route) =>
    route.fulfill({ status: 200, body: JSON.stringify({ access_token: 'token', user: { id: 1, email: 'w@test.com', role: 'worker' } }) })
  );
  await page.route('**/verify/status', async (route) =>
    route.fulfill({ status: 200, body: JSON.stringify({ verification_status: 'approved', latest_document: null }) })
  );
  await page.route('**/verify/upload', async (route) => route.fulfill({ status: 201, body: JSON.stringify({ id: 1, status: 'pending' }) }));
  await page.route('**/listings?q=*', async (route) =>
    route.fulfill({ status: 200, body: JSON.stringify({ results: [{ id: 2, title: 'Server', description: 'Hotel role', is_public: true, is_active: true }] }) })
  );
  await page.route('**/listings/2/apply', async (route) => route.fulfill({ status: 201, body: JSON.stringify({ id: 1 }) }));

  await page.goto('/register');
  await page.getByLabel('email').fill('w@test.com');
  await page.getByLabel('password').fill('Password1!');
  await page.getByLabel('role').selectOption('worker');
  await page.getByRole('button', { name: 'Register' }).click();
  await expect(page).toHaveURL(/login/);

  await page.getByLabel('email').fill('w@test.com');
  await page.getByLabel('password').fill('Password1!');
  await page.getByRole('button', { name: 'Login' }).click();
  await page.goto('/worker');
  await expect(page.getByText('Verification:')).toBeVisible();

  await page.getByLabel('search').fill('Server');
  await page.getByRole('button', { name: 'Search' }).click();
  await page.getByRole('button', { name: 'Apply' }).click();
});

test('employer journey: purchase -> create listing', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('j1hub_access_token', 'emp-token');
    localStorage.setItem('j1hub_user', JSON.stringify({ id: 2, email: 'e@test.com', role: 'employer' }));
  });
  await page.route('**/billing/create-checkout-session', async (route) => route.fulfill({ status: 200, body: JSON.stringify({ sessionId: 'sess_123' }) }));
  await page.route('**/listings', async (route) => route.fulfill({ status: 201, body: JSON.stringify({ id: 44 }) }));

  await page.goto('/employer');
  await page.getByRole('button', { name: 'Purchase listing credit' }).click();
  await page.getByPlaceholder('title').fill('Kitchen Staff');
  await page.getByPlaceholder('description').fill('Need experienced staff');
  await page.getByPlaceholder('contact value').fill('jobs@example.com');
  await page.getByRole('button', { name: 'Create listing' }).click();
  await expect(page.getByText('Listing created successfully.')).toBeVisible();
});

test('admin journey: review pending docs', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('j1hub_access_token', 'admin-token');
    localStorage.setItem('j1hub_user', JSON.stringify({ id: 3, email: 'a@test.com', role: 'admin' }));
  });
  await page.route('**/admin/verify/pending', async (route) =>
    route.fulfill({ status: 200, body: JSON.stringify([{ id: 5, filename: 'visa.pdf', user_id: 9 }]) })
  );
  await page.route('**/verify/5/approve', async (route) => route.fulfill({ status: 200, body: JSON.stringify({ id: 5, status: 'approved' }) }));

  await page.goto('/admin');
  await expect(page.getByText('visa.pdf')).toBeVisible();
  await page.getByRole('button', { name: 'Approve' }).click();
});
