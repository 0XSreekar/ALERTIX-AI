import { test, expect } from "@playwright/test";

test.describe("Smoke tests", () => {
  test("landing page loads", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Real-time multi-hazard intelligence")).toBeVisible();
    await expect(page.getByRole("link", { name: /Open Dashboard/ })).toBeVisible();
  });

  test("about page loads", async ({ page }) => {
    await page.goto("/about");
    await expect(page.getByText("About Alertix AI")).toBeVisible();
  });

  test("contact page loads", async ({ page }) => {
    await page.goto("/contact");
    await expect(page.getByText("Contact")).toBeVisible();
    await expect(page.getByRole("button", { name: /Send Message/ })).toBeVisible();
  });

  test("login page loads", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("button", { name: /Sign In/ })).toBeVisible();
  });

  test("dashboard redirects to login when not authenticated", async ({ page }) => {
    await page.goto("/dashboard");
    await page.waitForURL(/\/login/);
    await expect(page.getByRole("button", { name: /Sign In/ })).toBeVisible();
  });
});
