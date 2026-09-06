/*
  The phone layout, asserted rather than photographed. Created 2026-09.

  Written after a report from an iPhone: the raw log came out in three or four
  different font sizes, the two panes were split down the middle at 1fr/1fr with
  the divider unusable by finger, and the top bar sat there through everything.
  Each of those is a rule in `index.css` (or in `useHideOnScroll`) that a later
  edit could quietly undo, and none of them shows up on a desktop screen, so
  they are checked here instead of left to the next person with a phone.

  It runs in the same `npm run screenshots` pass as the capture spec and against
  the same stack; it writes nothing. To add a case, put it in the narrow or the
  wide `describe` - the viewport is what the two differ in.
*/

import { expect, test, type Page } from '@playwright/test'

const EXAMPLE = '915_jobshop_8workers'

/** Load an example through its deep link and wait until both panes are up. */
async function analyze(page: Page): Promise<void> {
  await page.goto(`/?example=${EXAMPLE}`)
  await expect(page.locator('.main .pane').first()).toBeVisible({ timeout: 30_000 })
  await page.waitForLoadState('networkidle')
  await page.waitForTimeout(400)
}

/** Scroll a pane the way a finger does: in steps, so the direction is readable. */
async function scrollPane(page: Page, by: number): Promise<void> {
  for (let i = 0; i < 8; i++) {
    await page.locator('.main .pane').first().evaluate((el, d) => el.scrollBy(0, d), by / 8)
    await page.waitForTimeout(40)
  }
  await page.waitForTimeout(300)
}

test.describe('narrow screen', () => {
  test.use({ viewport: { width: 390, height: 780 }, hasTouch: true, isMobile: true })

  test('the raw log has one font size', async ({ page }) => {
    // iOS Safari and Chrome inflate text per block when a block is much wider
    // than the screen, so the long log lines came out larger than the short
    // ones. `text-size-adjust: 100%` opts out; without it these differ.
    await analyze(page)
    const sizes = await page.$$eval('.logview .logline .txt', (els) =>
      Array.from(new Set(els.slice(0, 60).map((e) => getComputedStyle(e).fontSize))),
    )
    expect(sizes).toEqual(['12px'])
  })

  test('the panes stack and the divider drags vertically', async ({ page }) => {
    await analyze(page)
    const box = await page.locator('.splitter').boundingBox()
    expect(box).not.toBeNull()
    // Full width, thin: a horizontal strip between stacked panes, not a column.
    expect(box!.width).toBeGreaterThan(300)
    expect(box!.height).toBeLessThan(20)
    // The analysis gets the larger half by default.
    const main = await page.locator('.main').boundingBox()
    expect(box!.y - main!.y).toBeGreaterThan(main!.height * 0.5)

    // Pointer events, not page.mouse: the divider captures the pointer and reads
    // clientY, which is what a finger delivers.
    await page.locator('.splitter').dispatchEvent('pointerdown', {
      pointerId: 1,
      clientX: box!.x + 100,
      clientY: box!.y + 5,
      isPrimary: true,
      button: 0,
      pointerType: 'touch',
    })
    await page.evaluate((y) => {
      window.dispatchEvent(new PointerEvent('pointermove', { pointerId: 1, clientX: 100, clientY: y }))
      window.dispatchEvent(new PointerEvent('pointerup', { pointerId: 1 }))
    }, box!.y - 120)
    const vars = await page.locator('.main').evaluate((el) => ({
      top: el.style.getPropertyValue('--top'),
      left: el.style.getPropertyValue('--left'),
    }))
    expect(vars.top).not.toBe('')
    expect(vars.left).toBe('')
    const moved = await page.locator('.splitter').boundingBox()
    expect(moved!.y).toBeLessThan(box!.y - 50)
  })

  test('the top bar gets out of the way while reading', async ({ page }) => {
    await analyze(page)
    const bar = page.locator('.topbar')
    expect((await bar.boundingBox())!.y).toBe(0)
    const height = (await bar.boundingBox())!.height

    await scrollPane(page, 400)
    // Fully retreated: the whole bar height, so the panes get the room.
    expect((await bar.boundingBox())!.y).toBeLessThanOrEqual(-height + 1)

    await scrollPane(page, -400)
    expect((await bar.boundingBox())!.y).toBe(0)
  })
})

test.describe('wide screen', () => {
  test.use({ viewport: { width: 1400, height: 900 } })

  test('the top bar stays pinned', async ({ page }) => {
    // The hook toggles its class on every screen; only the narrow media query
    // acts on it. This is the assertion that keeps that rule where it belongs.
    await analyze(page)
    await scrollPane(page, 400)
    expect((await page.locator('.topbar').boundingBox())!.y).toBe(0)
  })
})
