import { Interactable, TextInput } from '@xrift/world-components'
import { normalizeCode, SUIT_FACING, type GalleryEntry } from '~/lib/gallery'
import { useSuit, useHenshin } from './SuitExhibit'
import { TextPlate } from './TextPlate'

interface CenterStageProps {
  code: string | null
  henshinTick: number
  entries: GalleryEntry[]
  infoLines: string[]
  onSummon: (code: string) => void
  onHenshin: () => void
  onResult: (line: string) => void
}

const CATALOG_MAX = 8

// 中央の召喚台: 呼出符コンソール(手入力)+収蔵カタログ(選んで召喚)+蒸着ボタン。
// 召喚・蒸着はインスタンス同期 — 来訪者全員が同じ儀式を目撃する
export function CenterStage({
  code, henshinTick, entries, infoLines, onSummon, onHenshin, onResult,
}: CenterStageProps) {
  const { vrm, vrma } = useSuit(code, true, onResult)
  useHenshin(vrm, vrma, henshinTick)

  return (
    <group>
      {/* 二段の円形プラットフォーム */}
      <mesh position={[0, 0.07, 0]} receiveShadow>
        <cylinderGeometry args={[2.3, 2.5, 0.14, 48]} />
        <meshStandardMaterial color="#1a2530" metalness={0.7} roughness={0.35} />
      </mesh>
      <mesh position={[0, 0.2, 0]} castShadow receiveShadow>
        <cylinderGeometry args={[1.5, 1.65, 0.14, 48]} />
        <meshStandardMaterial color="#212f3c" metalness={0.7} roughness={0.3} />
      </mesh>
      <mesh position={[0, 0.275, 0]}>
        <cylinderGeometry args={[1.52, 1.52, 0.015, 48]} />
        <meshBasicMaterial color="#38d9f1" />
      </mesh>
      {/* スーツ — rotateVRM0後の自然な向き(+Z=スポーン側)。Phase 2で実証済みの基準 */}
      <group position={[0, 0.28, 0]} rotation={[0, SUIT_FACING, 0]}>
        {vrm && <primitive object={vrm.scene} />}
      </group>
      {code && (
        <TextPlate lines={[code, '召喚中のスーツ']} position={[0, 2.7, 0]} width={1.8} />
      )}

      {/* 収蔵サマリ(ラフなメニュー — 台座右脇) */}
      <TextPlate lines={infoLines} position={[2.9, 1.5, 1.2]} rotation={[0, -0.5, 0]} width={2.1} />

      {/* 蒸着ボタン(赤い儀式スイッチ) */}
      <Interactable
        id="henshin-button"
        onInteract={() => onHenshin()}
        interactionText="蒸着!"
        enabled={!!vrm && !!vrma}
      >
        <group position={[1.6, 0, 1.9]}>
          <mesh position={[0, 0.5, 0]} castShadow>
            <cylinderGeometry args={[0.09, 0.12, 1.0, 12]} />
            <meshStandardMaterial color="#1c2833" metalness={0.6} roughness={0.4} />
          </mesh>
          <mesh position={[0, 1.05, 0]}>
            <sphereGeometry args={[0.14, 24, 16]} />
            <meshStandardMaterial
              color="#c0392b" emissive="#ff2200" emissiveIntensity={0.8}
              metalness={0.3} roughness={0.4}
            />
          </mesh>
        </group>
      </Interactable>

      {/* 召喚コンソール(呼出符の手入力) */}
      <TextInput
        id="summon-console"
        placeholder="呼出符 5文字 (例: PTAU3)"
        maxLength={12}
        interactionText="呼出符を入力"
        onSubmit={(value) => {
          const normalized = normalizeCode(value)
          if (normalized) onSummon(normalized)
        }}
      >
        <group position={[-1.7, 0, 2.0]} rotation={[0, Math.PI / 5, 0]}>
          <mesh position={[0, 0.45, 0]} castShadow>
            <boxGeometry args={[0.7, 0.9, 0.35]} />
            <meshStandardMaterial color="#141e28" metalness={0.6} roughness={0.4} />
          </mesh>
          <mesh position={[0, 0.93, -0.02]} rotation={[-0.5, 0, 0]}>
            <boxGeometry args={[0.62, 0.36, 0.04]} />
            <meshStandardMaterial
              color="#0a1620" emissive="#38d9f1" emissiveIntensity={0.5}
            />
          </mesh>
        </group>
      </TextInput>

      {/* 収蔵カタログ(プルダウン相当 — 選んで召喚するボード) */}
      <group position={[-3.1, 0, 1.4]} rotation={[0, 0.6, 0]}>
        <mesh position={[0, 1.45, -0.05]}>
          <boxGeometry args={[1.5, 2.7, 0.08]} />
          <meshStandardMaterial color="#0c141c" metalness={0.5} roughness={0.5} />
        </mesh>
        <TextPlate lines={['収蔵カタログ', '押して召喚']} position={[0, 2.55, 0.02]} width={1.3} />
        {entries.slice(0, CATALOG_MAX).map((entry, i) => {
          const accent = entry.palette?.emissive ?? entry.palette?.accent ?? '#9fdcff'
          const selected = entry.code === code
          return (
            <Interactable
              key={entry.code}
              id={`catalog-${entry.code}`}
              onInteract={() => onSummon(entry.code)}
              interactionText={`${entry.code} を召喚`}
            >
              <group position={[0, 2.12 - i * 0.26, 0.03]}>
                <mesh>
                  <boxGeometry args={[1.34, 0.22, 0.03]} />
                  <meshStandardMaterial
                    color={selected ? '#173242' : '#101a24'}
                    emissive={accent}
                    emissiveIntensity={selected ? 0.55 : 0.18}
                  />
                </mesh>
                <TextPlate lines={[entry.code]} position={[0, 0, 0.03]} width={1.1} aspect={5.2} accent={accent} />
              </group>
            </Interactable>
          )
        })}
      </group>
    </group>
  )
}
