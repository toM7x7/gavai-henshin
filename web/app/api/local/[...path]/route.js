// ローカル開発専用: リポジトリ隣の webdrop/<code>/ を配信する。
// Supabase 環境変数が設定されるとクライアントはこちらを使わなくなる。
import { promises as fs } from 'fs';
import path from 'path';

const WEBDROP = path.resolve(process.cwd(), '..', 'webdrop');

const MIME = {
  '.json': 'application/json',
  '.glb': 'model/gltf-binary',
  '.vrm': 'model/gltf-binary',
  '.vrma': 'model/gltf-binary',
  '.png': 'image/png',
};

export async function GET(_req, { params }) {
  // ローカル開発専用ルート — 本番(Vercel)では常に404
  // (ファイルシステム読み出しを外部に露出させない)
  if (process.env.NODE_ENV === 'production') {
    return new Response('not found', { status: 404 });
  }
  const { path: parts } = await params;
  const rel = (parts || []).join('/');
  // パス走査を遮断してから webdrop 配下だけを許可。
  // startsWith 単体は `webdrop-evil` のような兄弟ディレクトリを通すので
  // 「完全一致 or 区切り文字付き前方一致」で判定する
  const full = path.resolve(WEBDROP, rel);
  if (full !== WEBDROP && !full.startsWith(WEBDROP + path.sep)) {
    return new Response('forbidden', { status: 403 });
  }
  const target = (parts || []).length === 1
    ? path.join(full, 'suit-package.json')  // /api/local/<code> → manifest
    : full;
  try {
    const data = await fs.readFile(target);
    const type = MIME[path.extname(target).toLowerCase()] || 'application/octet-stream';
    return new Response(data, { headers: { 'content-type': type } });
  } catch {
    return new Response('not found', { status: 404 });
  }
}
