import { test, expect } from '@playwright/test';

const api = '**/api/v1';

test('worker can register, find a listing, apply, and see application status', async ({ page }) => {
  let applications: Array<{ id: number; user_id: number; listing_id: number; message: string; status: string }> = [];
  await page.route(`${api}/auth/register`, async (route) => route.fulfill({ status: 201, body: JSON.stringify({}) }));
  await page.route(`${api}/auth/login`, async (route) =>
    route.fulfill({ status: 200, body: JSON.stringify({ access_token: 'worker-token', user: { id: 1, email: 'w@test.com', role: 'worker' } }) })
  );
  await page.route(`${api}/verify/status`, async (route) =>
    route.fulfill({ status: 200, body: JSON.stringify({ verification_status: 'approved', latest_document: null }) })
  );
  await page.route(`${api}/listings/applications/mine`, async (route) =>
    route.fulfill({ status: 200, body: JSON.stringify({ results: applications, count: applications.length }) })
  );
  await page.route(`${api}/listings?q=*`, async (route) =>
    route.fulfill({ status: 200, body: JSON.stringify({ results: [{ id: 2, title: 'Server', description: 'Hotel role', is_public: true, is_active: true }], count: 1, pagination: {} }) })
  );
  await page.route(`${api}/listings/2/apply`, async (route) => {
    applications = [{ id: 10, user_id: 1, listing_id: 2, message: 'Interested in this role', status: 'new' }];
    await route.fulfill({ status: 201, body: JSON.stringify(applications[0]) });
  });

  await page.goto('/register');
  await page.getByLabel('email').fill('w@test.com');
  await page.getByLabel('password').fill('Password1!');
  await page.getByLabel('role').selectOption('worker');
  await page.getByRole('button', { name: 'Register' }).click();
  await expect(page).toHaveURL(/login/);

  await page.getByLabel('email').fill('w@test.com');
  await page.getByLabel('password').fill('Password1!');
  await page.getByRole('button', { name: 'Login' }).click();
  await expect(page).toHaveURL('/');
  await page.goto('/worker');
  await expect(page.getByText('Verification:')).toContainText('approved');
  await page.getByLabel('search').fill('Server');
  await page.getByRole('button', { name: 'Search' }).click();
  await page.getByRole('button', { name: 'Apply' }).click();
  await expect(page.getByRole('status')).toContainText('Application sent');
  await expect(page.getByText('Status: new')).toBeVisible();
});

test('employer loads account status and creates a listing', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('j1hub_access_token', 'emp-token');
    localStorage.setItem('j1hub_user', JSON.stringify({ id: 2, email: 'e@test.com', role: 'employer' }));
  });
  await page.route(`${api}/billing/status`, async (route) =>
    route.fulfill({ status: 200, body: JSON.stringify({ listing_credits: 1, has_active_subscription: false, active_until: null }) })
  );
  await page.route(`${api}/billing/history`, async (route) =>
    route.fulfill({ status: 200, body: JSON.stringify({ events: [], count: 0 }) })
  );
  await page.route(`${api}/listings/mine`, async (route) =>
    route.fulfill({ status: 200, body: JSON.stringify({ results: [], count: 0 }) })
  );
  await page.route(`${api}/listings`, async (route) => route.fulfill({ status: 201, body: JSON.stringify({ id: 44 }) }));

  await page.goto('/employer');
  await expect(page.getByText(/Listing credits: 1/)).toBeVisible();
  await page.getByPlaceholder('title').fill('Kitchen Staff');
  await page.getByPlaceholder('description').fill('Need experienced staff');
  await page.getByPlaceholder('contact value').fill('jobs@example.com');
  await page.getByRole('button', { name: 'Create listing' }).click();
  await expect(page.getByRole('status')).toContainText('Listing created successfully');
});

test('admin reads the paginated queue and approves a document', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('j1hub_access_token', 'admin-token');
    localStorage.setItem('j1hub_user', JSON.stringify({ id: 3, email: 'a@test.com', role: 'admin' }));
  });
  let pending = Array.from({ length: 21 }, (_, index) => ({
    id: index + 1,
    filename: `visa-${index + 1}.pdf`,
    user_id: 9,
    created_at: `2026-09-25T10:${String(index).padStart(2, '0')}:00`,
  }));
  await page.route((targetUrl) => targetUrl.pathname.endsWith('/api/v1/admin/verify/pending'), async (route) => {
    const url = new URL(route.request().url());
    const requestedPage = Number(url.searchParams.get('page') ?? '1');
    const perPageParameter = url.searchParams.get('per_page');
    expect(perPageParameter).toBe('20');
    const perPage = Number(perPageParameter);
    const totalPages = Math.ceil(pending.length / perPage);
    const pageNumber = requestedPage;
    const start = (pageNumber - 1) * perPage;
    const results = pending.slice(start, start + perPage);
    return route.fulfill({
      status: 200,
      body: JSON.stringify({
        results,
        count: results.length,
        pagination: {
          page: pageNumber,
          per_page: perPage,
          total: pending.length,
          total_pages: totalPages,
          has_next: pageNumber < totalPages,
          has_prev: pageNumber > 1,
        },
      }),
    });
  });
  await page.route(`${api}/admin/verify/21/approve`, async (route) => {
    pending = pending.filter((document) => document.id !== 21);
    await route.fulfill({ status: 200, body: JSON.stringify({ id: 21, status: 'approved' }) });
  });

  await page.goto('/admin');
  await expect(page.getByText('visa-1.pdf')).toBeVisible();
  await expect(page.getByText('visa-21.pdf')).not.toBeVisible();
  await expect(page.getByRole('status')).toHaveText('Page 1 of 2 (21 pending)');
  await page.getByRole('button', { name: 'Next page' }).click();
  await expect(page.getByText('visa-21.pdf')).toBeVisible();
  await expect(page.getByRole('status')).toHaveText('Page 2 of 2 (21 pending)');
  await page.getByRole('button', { name: 'Previous page' }).click();
  await expect(page.getByText('visa-1.pdf')).toBeVisible();
  await expect(page.getByRole('status')).toHaveText('Page 1 of 2 (21 pending)');
  await page.getByRole('button', { name: 'Next page' }).click();
  await page.getByRole('article').filter({ hasText: 'visa-21.pdf' }).getByRole('button', { name: 'Approve' }).click();
  await expect(page.getByText('visa-20.pdf')).toBeVisible();
  await expect(page.getByRole('status')).toHaveText('Page 1 of 1 (20 pending)');
  await expect(page.getByRole('button', { name: 'Previous page' })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Next page' })).toBeDisabled();
});

test('admin sees an empty queue without pagination controls', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('j1hub_access_token', 'admin-token');
    localStorage.setItem('j1hub_user', JSON.stringify({ id: 3, email: 'a@test.com', role: 'admin' }));
  });
  await page.route((url) => url.pathname.endsWith('/api/v1/admin/verify/pending'), async (route) =>
    route.fulfill({
      status: 200,
      body: JSON.stringify({
        results: [],
        count: 0,
        pagination: {
          page: 1,
          per_page: 20,
          total: 0,
          total_pages: 0,
          has_next: false,
          has_prev: false,
        },
      }),
    })
  );

  await page.goto('/admin');
  await expect(page.getByText('No pending documents.')).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Pending verification pages' })).toHaveCount(0);
});
