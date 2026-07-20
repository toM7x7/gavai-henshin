// 鍛造ギャラリー(Supabase public bucket)への接続。
// ★このワールドの検証目的そのもの: XRiftワールド実行時に外部URLをfetchできるか。
// URLは公開バケット(秘密ではない)。forgeが維持する gallery.json が台帳
const SUITS_BASE =
  'https://ddoedsybeuivbqtjgrrx.supabase.co/storage/v1/object/public/suits'

export interface GalleryEntry {
  code: string
  blueprint_id?: string
  intent?: string
  palette?: Record<string, string>
  created_at?: string
}

export async function fetchGallery(): Promise<GalleryEntry[]> {
  const res = await fetch(`${SUITS_BASE}/gallery.json`, { cache: 'no-store' })
  if (!res.ok) throw new Error(`gallery.json HTTP ${res.status}`)
  return res.json()
}

// 各スーツのマニフェストからVRMファイル名を引く(パッケージ契約 suit-package.v1)
export async function fetchSuitVrmUrl(code: string): Promise<string> {
  const res = await fetch(`${SUITS_BASE}/${code}/suit-package.json`, { cache: 'no-store' })
  if (!res.ok) throw new Error(`suit-package.json HTTP ${res.status}`)
  const manifest = (await res.json()) as { files?: { vrm?: string } }
  if (!manifest.files?.vrm) throw new Error('VRM未収録パッケージ')
  return `${SUITS_BASE}/${code}/${manifest.files.vrm}`
}
