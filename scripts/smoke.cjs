const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const url = process.env.APP_URL || 'http://127.0.0.1:5173';
const failures = [];

async function slider(page, selector, value) {
  await page.locator(selector).evaluate((input, next) => {
    input.value = next;
    input.dispatchEvent(new Event('input', { bubbles: true }));
  }, String(value));
}

(async () => {
  // Independently inspect the downloadable asset, not a mock or fixture.
  const data = fs.readFileSync(path.join(root, 'public/models/nomad-mk07.glb'));
  assert.equal(data.toString('utf8', 0, 4), 'glTF');
  assert.equal(data.readUInt32LE(4), 2);
  assert.equal(data.readUInt32LE(8), data.length);
  const document = JSON.parse(data.toString('utf8', 20, 20 + data.readUInt32LE(12)));
  assert.equal(document.meshes.length, 477);
  assert.equal(document.materials.length, 10);
  assert.ok(document.images.every(image => image.bufferView !== undefined), 'Textures must be embedded');
  assert.ok(document.nodes.filter(node => node.mesh === undefined).length >= 9, 'Assembly hierarchy must be preserved');
  for (const name of ['01', '02', '03', '04', '05']) {
    const material = document.materials.find(m => m.name.startsWith(name));
    assert.ok(material.pbrMetallicRoughness.baseColorTexture);
    assert.ok(material.pbrMetallicRoughness.metallicRoughnessTexture);
    assert.ok(material.normalTexture);
  }
  console.log('PASS: GLB structure, hierarchy, embedded PBR maps');

  const browser = await chromium.launch({
    executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium',
    headless: true,
    args: ['--no-sandbox', '--enable-unsafe-swiftshader', '--use-angle=swiftshader'],
  });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
    page.setDefaultTimeout(45000);
    page.on('pageerror', error => failures.push(error.message));
    page.on('console', message => { if (message.type() === 'error') failures.push(message.text()); });
    page.on('response', response => { if (response.status() >= 400) failures.push(`${response.status()} ${response.url()}`); });
    await page.goto(url);
    await page.waitForFunction(() => window.nomadDiagnostics?.().ready, null, { timeout: 90000 });
    const diagnostics = await page.evaluate(() => window.nomadDiagnostics());
    assert.equal(diagnostics.materials, 10);
    assert.equal(diagnostics.assemblies, 9);
    assert.ok(diagnostics.triangles > 140000);
    assert.ok(diagnostics.drawCalls < 120, 'Geometry batching should reduce draw calls');
    console.log('PASS: model rendered', JSON.stringify(diagnostics));
    await page.screenshot({ path: path.join(root, 'artifacts/viewer-desktop.png') });

    await page.locator('[data-light="hangar"]').click();
    assert.ok(await page.locator('[data-light="hangar"]').evaluate(el => el.classList.contains('selected')));
    await slider(page, '#explode', 75);
    assert.equal((await page.evaluate(() => window.nomadDiagnostics())).exploded, .75);
    await page.screenshot({ path: path.join(root, 'artifacts/viewer-exploded.png') });
    await page.locator('#wireframe').click();
    assert.equal((await page.evaluate(() => window.nomadDiagnostics())).wireframe, true);
    await page.locator('#solid').click();

    await page.locator('[data-tab="materials"]').click();
    assert.ok(await page.locator('#materials-panel').isVisible());
    await page.locator('[data-finish="desert"]').click();
    assert.equal(await page.locator('#finish-label').textContent(), 'Desert sand');
    await slider(page, '#roughness', 42);
    assert.equal(await page.locator('#roughness-value').textContent(), '42%');
    await slider(page, '#exposure', 120);
    assert.equal(await page.locator('#exposure-value').textContent(), '1.2');
    await page.locator('#rotate').click();
    assert.equal(await page.locator('#rotate').getAttribute('aria-pressed'), 'true');
    await page.locator('#reset').click();
    assert.equal(await page.locator('#rotate').getAttribute('aria-pressed'), 'false');
    assert.equal((await page.evaluate(() => window.nomadDiagnostics())).exploded, 0);
    assert.equal(await page.locator('#finish-label').textContent(), 'Field green');
    assert.equal(await page.locator('#roughness').inputValue(), '100');
    console.log('PASS: lighting, assembly separation, wireframe, finish, roughness, exposure, turntable, reset');

    await page.locator('[data-tab="overview"]').click();
    await page.locator('[data-camera="detail"]').click();
    await page.waitForTimeout(1100);
    assert.equal((await page.evaluate(() => window.nomadDiagnostics())).view, 'detail');
    await page.screenshot({ path: path.join(root, 'artifacts/viewer-detail.png') });
    await page.locator('[data-tab="specs"]').click();
    assert.ok(await page.locator('#specs-panel').isVisible());
    assert.equal(await page.locator('#triangle-count').textContent(), '148,992');

    const [glbDownload] = await Promise.all([page.waitForEvent('download'), page.locator('.download').click()]);
    assert.equal(glbDownload.suggestedFilename(), 'nomad-mk07.glb');
    assert.equal(fs.statSync(await glbDownload.path()).size, data.length);
    const [imageDownload] = await Promise.all([page.waitForEvent('download'), page.locator('#capture').click()]);
    assert.equal(imageDownload.suggestedFilename(), 'nomad-mk07.png');
    assert.ok(fs.statSync(await imageDownload.path()).size > 100000);
    console.log('PASS: camera presets, model download and PNG capture');

    await page.setViewportSize({ width: 390, height: 844 });
    await page.locator('#reset').click();
    await page.locator('[data-tab="overview"]').click();
    assert.ok(await page.locator('#inspector').isVisible());
    await page.locator('#panel-toggle').click();
    assert.equal(await page.locator('#panel-toggle').getAttribute('aria-expanded'), 'false');
    assert.equal(await page.locator('#inspector').isVisible(), false);
    await page.waitForFunction(() => !document.querySelector('#toast').classList.contains('visible'));
    await page.waitForTimeout(1000);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await page.screenshot({ path: path.join(root, 'artifacts/viewer-mobile.png') });
    assert.deepEqual(failures, [], 'Browser runtime and asset requests must be clean');
    console.log(JSON.stringify({ result: 'PASS', ...diagnostics, checks: 'GLB, embedded PBR maps, rendering, controls, camera, downloads, PNG capture, mobile layout', errors: failures }, null, 2));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
