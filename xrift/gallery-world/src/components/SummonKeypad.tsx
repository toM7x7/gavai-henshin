import { useState } from 'react'
import { CanvasTexture, SRGBColorSpace } from 'three'
import { Interactable } from '@xrift/world-components'
import { TextPlate } from './TextPlate'

// 呼出符 照合盤 — ワールド内で完結する3Dキーパッド。
// プラットフォームのTextInputはDOM/システムキーボードを呼ぶ設計のため、
// 没入中のVRセッションが中断される(実機で確認済みの仕様制約)。
// InteractableのキーだけならVR/デスクトップの双方でそのまま押せる

// 呼出符の字母(0/O/1/I除外の32字 — forgeの採番規約と同一)
const KEY_ROWS = ['ABCDEFGH', 'JKLMNPQR', 'STUVWXYZ', '23456789']
const PITCH = 0.185
const CODE_LEN = 5

// キー刻印のテクスチャは字母ごとに1枚を共有(32枚×128px)
const texCache = new Map<string, CanvasTexture>()
function keyTexture(label: string, accent: string): CanvasTexture {
  const cacheKey = `${label}|${accent}`
  const hit = texCache.get(cacheKey)
  if (hit) return hit
  const can = document.createElement('canvas')
  can.width = 128
  can.height = 128
  const g = can.getContext('2d')!
  g.fillStyle = 'rgba(8, 15, 22, 0.96)'
  g.fillRect(0, 0, 128, 128)
  g.strokeStyle = accent
  g.lineWidth = 3
  g.strokeRect(5, 5, 118, 118)
  g.fillStyle = accent
  g.font = 'bold 64px "Segoe UI", "Hiragino Sans", sans-serif'
  g.textAlign = 'center'
  g.textBaseline = 'middle'
  g.fillText(label, 64, 68)
  const tex = new CanvasTexture(can)
  tex.colorSpace = SRGBColorSpace
  texCache.set(cacheKey, tex)
  return tex
}

interface KeyCapProps {
  id: string
  label: string
  position: [number, number, number]
  onPress: () => void
  hint?: string
  accent?: string
  width?: number
}

function KeyCap({ id, label, position, onPress, hint, accent = '#9fdcff', width = 0.16 }: KeyCapProps) {
  return (
    <Interactable id={id} onInteract={onPress} interactionText={hint ?? label}>
      <group position={position}>
        <mesh castShadow>
          <boxGeometry args={[width, 0.16, 0.03]} />
          <meshStandardMaterial color="#101a24" metalness={0.5} roughness={0.5} />
        </mesh>
        <mesh position={[0, 0, 0.017]}>
          <planeGeometry args={[width * 0.92, 0.147]} />
          <meshBasicMaterial map={keyTexture(label, accent)} transparent />
        </mesh>
      </group>
    </Interactable>
  )
}

interface SummonKeypadProps {
  onSummon: (code: string) => void
}

export function SummonKeypad({ onSummon }: SummonKeypadProps) {
  const [input, setInput] = useState('')
  const press = (ch: string) => setInput((s) => (s.length < CODE_LEN ? s + ch : s))
  const ready = input.length === CODE_LEN

  return (
    <group position={[-1.9, 0, 2.0]} rotation={[0, Math.PI / 5, 0]}>
      {/* 照合盤の筐体(手前へ傾けた操作面) */}
      <mesh position={[0, 0.28, -0.06]} castShadow>
        <boxGeometry args={[0.6, 0.56, 0.3]} />
        <meshStandardMaterial color="#141e28" metalness={0.6} roughness={0.45} />
      </mesh>
      <group position={[0, 0.92, 0]} rotation={[-0.42, 0, 0]}>
        <mesh position={[0, -0.05, -0.045]}>
          <boxGeometry args={[1.66, 1.42, 0.06]} />
          <meshStandardMaterial color="#0c141c" metalness={0.5} roughness={0.5} />
        </mesh>
        <TextPlate lines={['呼出符 照合盤']} width={1.05} aspect={6} position={[0, 0.56, 0.01]} />
        {/* 打刻中の符号表示 */}
        <TextPlate
          lines={[`GAVAI-${input.padEnd(CODE_LEN, '·')}`]}
          width={1.3}
          aspect={4.5}
          position={[0, 0.4, 0.01]}
          accent="#38d9f1"
        />
        {/* 字母キー 8×4 */}
        {KEY_ROWS.map((row, r) =>
          row.split('').map((ch, c) => (
            <KeyCap
              key={ch}
              id={`key-${ch}`}
              label={ch}
              position={[(c - 3.5) * PITCH, 0.2 - r * PITCH, 0.01]}
              onPress={() => press(ch)}
            />
          )),
        )}
        {/* 操作行: 一字削除 / 全消去 / 照合(5文字で有効) */}
        <KeyCap
          id="key-back"
          label="⌫"
          hint="一字削除"
          accent="#d9b45f"
          position={[-0.55, -0.6, 0.01]}
          width={0.34}
          onPress={() => setInput((s) => s.slice(0, -1))}
        />
        <KeyCap
          id="key-clear"
          label="消去"
          hint="全て消去"
          accent="#d9b45f"
          position={[-0.14, -0.6, 0.01]}
          width={0.34}
          onPress={() => setInput('')}
        />
        <Interactable
          id="key-submit"
          onInteract={() => {
            if (!ready) return
            onSummon(`GAVAI-${input}`)
            setInput('')
          }}
          interactionText={ready ? `GAVAI-${input} を照合して召喚` : '呼出符は5文字'}
          enabled={ready}
        >
          <group position={[0.42, -0.6, 0.01]}>
            <mesh castShadow>
              <boxGeometry args={[0.6, 0.16, 0.03]} />
              <meshStandardMaterial
                color={ready ? '#173242' : '#101a24'}
                emissive="#38d9f1"
                emissiveIntensity={ready ? 0.6 : 0.12}
              />
            </mesh>
            <TextPlate lines={['照合・召喚']} width={0.54} aspect={4} position={[0, 0, 0.017]} accent="#9fdcff" />
          </group>
        </Interactable>
      </group>
    </group>
  )
}
