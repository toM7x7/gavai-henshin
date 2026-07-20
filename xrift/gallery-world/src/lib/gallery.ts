// 鍛造ギャラリー(公開バケット)への接続。
// XRiftワールドは実行時fetchが権限宣言制で許可される(xrift.json permissions) —
// 鍛造するだけでこのワールドに新スーツが並ぶ構造の土台
const SUITS_BASE =
  'https://ddoedsybeuivbqtjgrrx.supabase.co/storage/v1/object/public/suits'

// スーツの正面補正(全展示共通)。VRM0はrotateVRM0後に+Z正面で立つ =
// 追加回転は不要、が実機実証済みの基準。もし実機で背面になったら
// ここを Math.PI にして再アップ(1行で全台座に効く)
export const SUIT_FACING = 0

export interface GalleryEntry {
  code: string
  blueprint_id?: string
  intent?: string
  palette?: Record<string, string>
  created_at?: string
}

export interface SuitFiles {
  vrmUrl: string
  vrmaUrl: string | null
}

export async function fetchGallery(): Promise<GalleryEntry[]> {
  const res = await fetch(`${SUITS_BASE}/gallery.json`, { cache: 'no-store' })
  if (!res.ok) throw new Error(`gallery.json HTTP ${res.status}`)
  return res.json()
}

// 各スーツのマニフェストからVRM/VRMAのURLを引く(パッケージ契約 suit-package.v1)
export async function fetchSuitFiles(code: string): Promise<SuitFiles> {
  const res = await fetch(`${SUITS_BASE}/${code}/suit-package.json`, { cache: 'no-store' })
  if (!res.ok) throw new Error(`suit-package.json HTTP ${res.status}`)
  const manifest = (await res.json()) as { files?: { vrm?: string; vrma?: string } }
  if (!manifest.files?.vrm) throw new Error('VRM未収録パッケージ')
  return {
    vrmUrl: `${SUITS_BASE}/${code}/${manifest.files.vrm}`,
    vrmaUrl: manifest.files.vrma ? `${SUITS_BASE}/${code}/${manifest.files.vrma}` : null,
  }
}

// 呼出符入力の正規化(webのGAVAI-プレフィックス入力と同じ規約)
export function normalizeCode(input: string): string {
  const tail = input
    .toUpperCase()
    .replace(/^GAVAI-?/, '')
    .replace(/[^A-Z0-9]/g, '')
    .slice(0, 5)
  return tail ? `GAVAI-${tail}` : ''
}

// 逐次ロードキュー: VRM(10MB級)の同時多発ダウンロード/パースで
// 入場直後が固まるのを防ぐ。1体ずつ流す
let chain: Promise<unknown> = Promise.resolve()
export function enqueueLoad<T>(job: () => Promise<T>): Promise<T> {
  const next = chain.then(job, job)
  chain = next.catch(() => undefined)
  return next
}

// 訪問ごとに展示が入れ替わる簡易シャッフル(Fisher–Yates)
export function shuffled<T>(arr: T[]): T[] {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}
