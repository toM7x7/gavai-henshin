// ワールド実写サムネイル撮影 — 本物のChromeでワールドを実レンダして撮る。
// 前提: dev サーバ稼働中(localhost:5173)。?shot=1 でカメラが定点に固定される。
// 実行: node scripts/shot.mjs → scripts/shot-raw.png
import puppeteer from 'puppeteer-core'

const CHROME = process.env.CHROME_PATH
  ?? 'C:/Program Files/Google/Chrome/Application/chrome.exe'

// headlessはWebGL合成が白飛びする環境があるため、実GPUのheadfulで描く
// (撮影中だけChromeウィンドウが一瞬開く)
const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: false,
  defaultViewport: { width: 1600, height: 900 },
  args: [
    '--window-size=1620,1010',
    '--mute-audio',
    '--no-first-run',
  ],
})
try {
  const page = await browser.newPage()
  page.on('console', (m) => {
    if (m.type() === 'error' || m.type() === 'warn') console.log(`[page:${m.type()}]`, m.text().slice(0, 160))
  })
  page.on('pageerror', (e) => console.log('[pageerror]', String(e).slice(0, 200)))
  await page.goto('http://localhost:5173/?shot=1', {
    waitUntil: 'networkidle2',
    timeout: 120_000,
  })
  console.log('page loaded — waiting for suits...')
  // スーツVRMのロード(逐次キュー)を待つ: vrm取得5件以上、最大150秒
  await page
    .waitForFunction(
      () =>
        performance
          .getEntriesByType('resource')
          .filter((r) => r.name.includes('vrm.vrm')).length >= 5,
      { timeout: 150_000, polling: 2000 },
    )
    .catch(() => console.log('suit wait timeout — 撮れているだけで撮影続行'))
  await new Promise((r) => setTimeout(r, 10_000)) // パース+描画の落ち着き待ち
  // UIオーバーレイ(マウスロック案内等)を隠す — canvasとその祖先だけ残す
  await page.evaluate(() => {
    const keep = new Set()
    document.querySelectorAll('canvas').forEach((c) => {
      let n = c
      while (n) { keep.add(n); n = n.parentElement }
    })
    document.body.querySelectorAll('*').forEach((el) => {
      if (!keep.has(el) && !el.querySelector('canvas')) el.style.visibility = 'hidden'
    })
  })
  await new Promise((r) => setTimeout(r, 800))
  // コンポジタ非依存の直接キャプチャ: shotイベント→同期render→toDataURL
  const dataUrl = await page.evaluate(() => {
    window.dispatchEvent(new Event('gavai-shot'))
    const canvas = document.querySelector('canvas')
    return canvas && canvas.dataset ? (canvas.dataset.shot ?? null) : null
  })
  if (!dataUrl) throw new Error('capture failed — dataset.shot is empty')
  const base64 = dataUrl.replace(/^data:image\/png;base64,/, '')
  const { writeFileSync } = await import('node:fs')
  writeFileSync('scripts/shot-raw.png', Buffer.from(base64, 'base64'))
  console.log('saved scripts/shot-raw.png', Math.round(base64.length / 1024), 'KB')
} finally {
  await browser.close()
}
