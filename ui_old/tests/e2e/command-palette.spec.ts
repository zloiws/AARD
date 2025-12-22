import { test, expect } from '@playwright/test'

test.describe('Command Palette', () => {
  test('should open command palette with Cmd+K', async ({ page }) => {
    await page.goto('/')
    
    // Press Cmd+K (or Ctrl+K on Windows)
    await page.keyboard.press('Meta+K')
    
    // Check if command palette dialog is visible
    await expect(page.getByPlaceholder('Type a command or search...')).toBeVisible()
  })

  test('should close command palette with Escape', async ({ page }) => {
    await page.goto('/')
    
    // Open palette
    await page.keyboard.press('Meta+K')
    await expect(page.getByPlaceholder('Type a command or search...')).toBeVisible()
    
    // Close with Escape
    await page.keyboard.press('Escape')
    
    // Verify it's closed
    await expect(page.getByPlaceholder('Type a command or search...')).not.toBeVisible()
  })

  test('should display navigation commands', async ({ page }) => {
    await page.goto('/')
    
    await page.keyboard.press('Meta+K')
    
    // Check for navigation commands
    await expect(page.getByText('Go to Dashboard')).toBeVisible()
    await expect(page.getByText('View All Tasks')).toBeVisible()
    await expect(page.getByText('View Agents')).toBeVisible()
  })
})
