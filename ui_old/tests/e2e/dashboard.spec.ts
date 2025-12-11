import { test, expect } from '@playwright/test'

test.describe('Dashboard', () => {
  test('should load dashboard successfully', async ({ page }) => {
    await page.goto('/')
    
    // Check if the main heading is visible
    await expect(page.getByText('Mission Control')).toBeVisible()
    
    // Check if metrics cards are visible
    await expect(page.getByText('Active Tasks')).toBeVisible()
    await expect(page.getByText('Completed')).toBeVisible()
    await expect(page.getByText('Pending')).toBeVisible()
    await expect(page.getByText('Failed')).toBeVisible()
  })

  test('should display AARD header', async ({ page }) => {
    await page.goto('/')
    
    await expect(page.getByText('AARD')).toBeVisible()
    await expect(page.getByText('AI Agent Research Dashboard')).toBeVisible()
  })

  test('should show command palette shortcut hint', async ({ page }) => {
    await page.goto('/')
    
    await expect(page.getByText('Press')).toBeVisible()
    await expect(page.getByText('Cmd+K')).toBeVisible()
  })
})
