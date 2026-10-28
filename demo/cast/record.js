// Record an animated cast page to video: node record.js cast.html out-dir
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [page_, outDir] = process.argv.slice(2);
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1000, height: 650 },
    recordVideo: { dir: outDir, size: { width: 1000, height: 650 } } });
  const page = await ctx.newPage();
  await page.goto('file://' + path.resolve(page_));
  await page.waitForFunction(() => document.title === 'done', null, { timeout: 600000 });
  const video = page.video();
  await ctx.close();
  console.log(await video.path());
  await browser.close();
})();
