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
  const { path: parts } = await params;
  const rel = (parts || []).join('/');
  // パス走査を遮断してから webdrop 配下だけを許可
  const full = path.resolve(WEBDROP, rel);
  if (!full.startsWith(WEBDROP)) {
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
