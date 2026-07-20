import { useEffect, useState } from 'react'
import { RigidBody } from '@react-three/rapier'
import { SpawnPoint } from '@xrift/world-components'
import { fetchGallery, type GalleryEntry } from '~/lib/gallery'
import { SuitExhibit } from '~/components/SuitExhibit'
import { TextPlate } from '~/components/TextPlate'

export interface WorldProps {
  position?: [number, number, number]
  scale?: number
}

// 蒸着庫(技術検証v0): 目的は「XRiftワールドから外部ギャラリーを実行時fetchできるか」の確定。
// 成立すれば、鍛造するだけでこのワールドに新スーツが並ぶ(再アップロード不要=A案)。
// 中央のステータス板が計測器 — 入場して読めば検証結果がわかる
export const World: React.FC<WorldProps> = ({ position = [0, 0, 0], scale = 1 }) => {
  const [lines, setLines] = useState<string[]>([
    '蒸着庫 — 外部接続検証',
    'gallery.json 照合中…',
  ])
  const [entries, setEntries] = useState<GalleryEntry[]>([])

  useEffect(() => {
    ;(async () => {
      try {
        const gallery = await fetchGallery()
        const latest = [...gallery]
          .sort((a, b) => (b.created_at ?? '').localeCompare(a.created_at ?? ''))
          .slice(0, 3)
        setEntries(latest)
        setLines((prev) => [
          prev[0],
          `✓ gallery.json OK — 登録 ${gallery.length}体 / 展示 ${latest.length}体`,
        ])
      } catch (e) {
        setLines((prev) => [
          prev[0],
          `✗ 外部fetch失敗: ${String((e as Error)?.message ?? e)}`,
          'A案不成立 — B案(鍛造時の再アップロード方式)へ切替',
        ])
      }
    })()
  }, [])

  const report = (line: string) => setLines((prev) => [...prev, line])

  // 展示台の配置: スポーン(z=6)から見て正面の弧
  const slots: [number, number, number][] = [
    [-3, 0, -3],
    [0, 0, -4],
    [3, 0, -3],
  ]

  return (
    <group position={position} scale={scale}>
      {/* ========== 環境・照明(蒸着執行録の世界観: 暗部+シアン) ========== */}
      <color attach="background" args={['#070d13']} />
      <fog attach="fog" args={['#070d13', 18, 45]} />
      <ambientLight intensity={0.55} />
      <directionalLight position={[4, 8, 5]} intensity={1.4} castShadow />
      <pointLight position={[0, 3, -4]} intensity={6} color="#38d9f1" distance={12} />
      <gridHelper args={[36, 36, '#2a5a6a', '#16232c']} position={[0, 0.01, 0]} />

      {/* ========== 床 ========== */}
      <RigidBody type="fixed" colliders="cuboid" restitution={0} friction={0}>
        <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
          <planeGeometry args={[36, 36]} />
          <meshStandardMaterial color="#101820" roughness={0.85} metalness={0.2} />
        </mesh>
      </RigidBody>

      {/* ========== 計測板(検証結果の表示 = このワールドの主役) ========== */}
      <TextPlate lines={lines} position={[0, 2.8, -7.5]} width={5.4} />

      {/* ========== スーツ展示(外部fetch成立時のみ現れる) ========== */}
      {entries.map((entry, i) => (
        <SuitExhibit
          key={entry.code}
          entry={entry}
          position={slots[i % slots.length]}
          onResult={report}
        />
      ))}

      {/* ========== スポーン ========== */}
      <group position={[0, 0, 6]}>
        <SpawnPoint />
      </group>
    </group>
  )
}
