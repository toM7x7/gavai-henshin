import { useEffect, useState } from 'react'
import { RigidBody } from '@react-three/rapier'
import { SpawnPoint, useInstanceState } from '@xrift/world-components'
import { fetchGallery, shuffled, type GalleryEntry } from '~/lib/gallery'
import { AlcoveExhibit } from '~/components/SuitExhibit'
import { CenterStage } from '~/components/CenterStage'
import { TextPlate } from '~/components/TextPlate'

export interface WorldProps {
  position?: [number, number, number]
  scale?: number
}

const ALCOVE_COUNT = 6

// 蒸着庫 Phase 2: スーツ格納庫ホール。
// 壁面アルコーブに鍛造スーツが並び(訪問ごとにシャッフル)、中央の召喚台では
// 呼出符で任意のスーツを召喚して蒸着モーション(VRMA)を見られる。
// 展示は実行時fetch — 鍛造するだけで収蔵が増える(再アップロード不要)
export const World: React.FC<WorldProps> = ({ position = [0, 0, 0], scale = 1 }) => {
  const [lines, setLines] = useState<string[]>(['蒸着庫 — 収蔵記録', '照合中…'])
  const [alcoves, setAlcoves] = useState<GalleryEntry[]>([])
  const [latestCode, setLatestCode] = useState<string | null>(null)
  // 召喚台の状態はインスタンス同期 — 全員が同じスーツと儀式を見る
  const [centerCode, setCenterCode] = useInstanceState<string>('center-code', '')
  const [henshinTick, setHenshinTick] = useInstanceState<number>('center-henshin', 0)

  useEffect(() => {
    ;(async () => {
      try {
        const gallery = await fetchGallery()
        const sorted = [...gallery].sort((a, b) =>
          (b.created_at ?? '').localeCompare(a.created_at ?? ''))
        setLatestCode(sorted[0]?.code ?? null)
        setAlcoves(shuffled(gallery).slice(0, ALCOVE_COUNT))
        setLines((prev) => [
          prev[0],
          `✓ 収蔵 ${gallery.length}体 / 展示 ${Math.min(gallery.length, ALCOVE_COUNT)}体`,
          '召喚台に呼出符を打ち込めば任意のスーツを呼べる',
        ])
      } catch (e) {
        setLines((prev) => [
          prev[0],
          `✗ 収蔵庫に接続できない: ${String((e as Error)?.message ?? e)}`,
        ])
      }
    })()
  }, [])

  // 最新スーツを既定で召喚台へ(誰かが召喚済みなら尊重する)
  useEffect(() => {
    if (latestCode && !centerCode) setCenterCode(latestCode)
  }, [latestCode, centerCode])

  const report = (line: string) =>
    setLines((prev) => (prev.length > 9 ? [...prev.slice(0, 2), line] : [...prev, line]))

  return (
    <group position={position} scale={scale}>
      {/* ========== 環境(格納庫: 暗部+シアン) ========== */}
      <color attach="background" args={['#060b11']} />
      <fog attach="fog" args={['#060b11', 20, 48]} />
      <ambientLight intensity={0.5} />
      <directionalLight position={[4, 9, 6]} intensity={1.1} castShadow />
      <pointLight position={[0, 4.5, 0]} intensity={9} color="#38d9f1" distance={13} />
      <gridHelper args={[44, 44, '#264a58', '#121e26']} position={[0, 0.01, 0]} />

      {/* ========== 床 ========== */}
      <RigidBody type="fixed" colliders="cuboid" restitution={0} friction={0}>
        <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
          <planeGeometry args={[44, 44]} />
          <meshStandardMaterial color="#0e161e" roughness={0.85} metalness={0.25} />
        </mesh>
      </RigidBody>

      {/* ========== 壁面アルコーブ(後方の弧) ========== */}
      {alcoves.map((entry, i) => {
        const a = (i - (alcoves.length - 1) / 2) * (Math.PI / 5.2)
        const pos: [number, number, number] = [Math.sin(a) * 8.5, 0, -Math.cos(a) * 8.5]
        const rotY = Math.atan2(-pos[0], -pos[2]) + Math.PI
        return (
          <AlcoveExhibit
            key={entry.code}
            entry={entry}
            position={pos}
            rotationY={rotY}
            onResult={report}
          />
        )
      })}

      {/* ========== 中央召喚台 ========== */}
      <CenterStage
        code={centerCode || null}
        henshinTick={henshinTick}
        onSummon={(code) => {
          setCenterCode(code)
          report(`⚡ ${code} を召喚`)
        }}
        onHenshin={() => setHenshinTick((t) => t + 1)}
        onResult={report}
      />

      {/* ========== 収蔵記録板(右手側) ========== */}
      <TextPlate
        lines={lines}
        position={[7.8, 2.3, 3.2]}
        rotation={[0, -Math.PI / 3, 0]}
        width={3.8}
      />

      {/* ========== スポーン ========== */}
      <group position={[0, 0, 6.5]}>
        <SpawnPoint />
      </group>
    </group>
  )
}
