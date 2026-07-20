import { useEffect, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { AnimationMixer, LoopOnce } from 'three'
import { Interactable, TextInput } from '@xrift/world-components'
import { createVRMAnimationClip } from '@pixiv/three-vrm-animation'
import { normalizeCode } from '~/lib/gallery'
import { useSuit } from './SuitExhibit'
import { TextPlate } from './TextPlate'

interface CenterStageProps {
  code: string | null
  henshinTick: number
  onSummon: (code: string) => void
  onHenshin: () => void
  onResult: (line: string) => void
}

// 中央の召喚台(トニーの組立プラットフォームの意匠):
// 呼出符コンソールでスーツを召喚し、蒸着ボタンでヘンシンモーション(VRMA)が走る。
// 召喚・蒸着はインスタンス同期 — 来訪者全員が同じ儀式を目撃する
export function CenterStage({ code, henshinTick, onSummon, onHenshin, onResult }: CenterStageProps) {
  const { vrm, vrma } = useSuit(code, true, onResult)
  const mixerRef = useRef<AnimationMixer | null>(null)

  useEffect(() => {
    mixerRef.current = null  // スーツ入替でモーションを破棄
  }, [vrm])

  useEffect(() => {
    if (!vrm || !vrma || henshinTick === 0) return
    const clip = createVRMAnimationClip(vrma, vrm)
    const mixer = new AnimationMixer(vrm.scene)
    const action = mixer.clipAction(clip)
    action.setLoop(LoopOnce, 1)
    action.clampWhenFinished = true  // 見得で止める
    action.play()
    mixerRef.current = mixer
  }, [henshinTick, vrm, vrma])

  useFrame((_, dt) => {
    mixerRef.current?.update(dt)
    vrm?.update(dt)
  })

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
      <group position={[0, 0.28, 0]}>
        {vrm && <primitive object={vrm.scene} />}
      </group>
      {code && (
        <TextPlate lines={[code, '召喚中のスーツ']} position={[0, 2.7, 0]} width={1.8} />
      )}

      {/* 蒸着ボタン(赤い儀式スイッチ) */}
      <Interactable
        id="henshin-button"
        onInteract={() => onHenshin()}
        interactionText="蒸着!"
        enabled={!!vrm && !!vrma}
      >
        <group position={[1.6, 0, 1.6]}>
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

      {/* 召喚コンソール(呼出符の書き込み台) */}
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
        <group position={[-1.9, 0, 1.9]} rotation={[0, Math.PI / 5, 0]}>
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
    </group>
  )
}
