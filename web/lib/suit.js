// 呼出符 → パッケージURL解決。
// 本番: Supabase Storage の public バケット `suits`。
// ローカル開発(env未設定): /api/local が ../webdrop/<code>/ を配信する。
// プロジェクトURL以外の値(末尾スラッシュ・/rest/v1 付き等)を貼っても動くよう正規化
const SUPA = (process.env.NEXT_PUBLIC_SUPABASE_URL || '')
  .replace(/\/(rest|storage|auth)\/v1\/?$/, '')
  .replace(/\/+$/, '') || null;

export function packageBase(code) {
  const safe = String(code || '').toUpperCase().replace(/[^A-Z0-9-]/g, '');
  if (SUPA) return `${SUPA}/storage/v1/object/public/suits/${safe}`;
  return `/api/local/${safe}`;
}

export async function fetchManifest(code) {
  const res = await fetch(`${packageBase(code)}/suit-package.json`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`呼出符 ${code} は登録されていません (${res.status})`);
  return res.json();
}

export function fileUrl(code, name) {
  return `${packageBase(code)}/${name}`;
}

export function galleryUrl() {
  if (SUPA) return `${SUPA}/storage/v1/object/public/suits/gallery.json`;
  return '/api/local/gallery.json';
}

// 鎧メッシュの判別 — VRMは結合済み "armor_suit"、assembly.glb は armor_* グループ。
// 蒸着体験は「素体で始まり、合言葉で鎧が装着される」: この分離が儀式の土台
export const isArmorObject = (o) => {
  let n = o;
  while (n) {
    if (/armor/i.test(n.name || '')) return true;
    n = n.parent;
  }
  return false;
};

export const armorMeshes = (root) => {
  const out = [];
  root.traverse((o) => { if (o.isMesh && isArmorObject(o)) out.push(o); });
  return out;
};

export const setArmorVisible = (root, visible) =>
  armorMeshes(root).forEach((m) => { m.visible = visible; });
