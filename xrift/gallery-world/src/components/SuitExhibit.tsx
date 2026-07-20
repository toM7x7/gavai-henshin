import { useEffect, useRef, useState } from 'react'
import { useFrame } from '@react-three/fiber'
import { AnimationMixer, LoopOnce } from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { Interactable, useInstanceState } from '@xrift/world-components'
import { VRMLoaderPlugin, VRMUtils, type VRM } from '@pixiv/three-vrm'
import {
  VRMAnimationLoaderPlugin,
  createVRMAnimationClip,
  type VRMAnimation,
} from '@pixiv/three-vrm-animation'
import { enqueueLoad, fetchSuitFiles, SUIT_FACING, type GalleryEntry } from '~/lib/gallery'
import { TextPlate } from './TextPlate'

// スーツVRM(+VRMA)の実行時ロード。逐次キューで1体ずつ流し、
// 入れ替え時は旧モデルのGPU資源を返却する
export function useSuit(
  code: string | null,
  withAnim: boolean,
  onResult?: (line: string) => void,
) {
  const [vrm, setVrm] = useState<VRM | null>(null)
  const [vrma, setVrma] = useState<VRMAnimation | null>(null)

  useEffect(() => {
    if (!code) return
    let disposed = false
    let loaded: VRM | null = null
    setVrm(null)
    setVrma(null)
    enqueueLoad(async () => {
      try {
        const files = await fetchSuitFiles(code)
        const loader = new GLTFLoader()
        loader.register((parser) => new VRMLoaderPlugin(parser))
        loader.register((parser) => new VRMAnimationLoaderPlugin(parser))
        const gltf = await loader.loadAsync(files.vrmUrl)
        loaded = gltf.userData.vrm as VRM
        VRMUtils.rotateVRM0(loaded)
        let anim: VRMAnimation | null = null
        if (withAnim && files.vrmaUrl) {
          try {
            const ag = await loader.loadAsync(files.vrmaUrl)
            anim = (ag.userData.vrmAnimations ?? [])[0] ?? null
          } catch {
            anim = null
          }
        }
        if (disposed) return
        setVrm(loaded)
        setVrma(anim)
      } catch (e) {
        onResult?.(`✗ ${code} ${String((e as Error)?.message ?? e)}`)
      }
    })
    return () => {
      disposed = true
      if (loaded) VRMUtils.deepDispose(loaded.scene)  // 入替時にGPUメモリを返す
    }
  }, [code, withAnim])

  return { vrm, vrma }
}

// 蒸着モーション(VRMA)の再生管理 — tickが進むたびに頭から再生し、見得で止める
export function useHenshin(vrm: VRM | null, vrma: VRMAnimation | null, tick: number) {
  const mixerRef = useRef<AnimationMixer | null>(null)

  useEffect(() => {
    mixerRef.current = null  // スーツ入替でモーションを破棄
  }, [vrm])

  useEffect(() => {
    if (!vrm || !vrma || tick === 0) return
    const clip = createVRMAnimationClip(vrma, vrm)
    const mixer = new AnimationMixer(vrm.scene)
    const action = mixer.clipAction(clip)
    action.setLoop(LoopOnce, 1)
    action.clampWhenFinished = true
    action.play()
    mixerRef.current = mixer
  }, [tick, vrm, vrma])

  useFrame((_, dt) => {
    mixerRef.current?.update(dt)
    vrm?.update(dt)
  })
}

interface AlcoveExhibitProps {
  entry: GalleryEntry
  position: [number, number, number]
  rotationY: number
  onSummon: (code: string) => void
  onResult: (line: string) => void
}

// 格納庫の壁面アルコーブ1基: 背光フレーム+台座+スーツ+符号プレート。
// 台座ごとに [蒸着](その場でモーション) と [召喚](中央台へ呼ぶ) のボタンを持つ
export function AlcoveExhibit({ entry, position, rotationY, onSummon, onResult }: AlcoveExhibitProps) {
  const { vrm, vrma } = useSuit(entry.code, true, onResult)
  // 台座ごとの蒸着もインスタンス同期 — 誰かが押せば全員に見える
  const [tick, setTick] = useInstanceState<number>(`henshin-${entry.code}`, 0)
  useHenshin(vrm, vrma, tick)

  const accent = entry.palette?.emissive ?? entry.palette?.accent ?? '#9fdcff'

  return (
    <group position={position} rotation={[0, rotationY, 0]}>
      {/* 背面パネル+発光フレーム */}
      <mesh position={[0, 1.55, -1.15]}>
        <boxGeometry args={[2.5, 3.1, 0.12]} />
        <meshStandardMaterial color="#0c141c" roughness={0.6} metalness={0.4} />
      </mesh>
      {[-1.2, 1.2].map((x) => (
        <mesh key={x} position={[x, 1.55, -1.08]}>
          <boxGeometry args={[0.06, 3.1, 0.06]} />
          <meshBasicMaterial color={accent} />
        </mesh>
      ))}
      <mesh position={[0, 3.08, -1.08]}>
        <boxGeometry args={[2.46, 0.06, 0.06]} />
        <meshBasicMaterial color={accent} />
      </mesh>
      {/* 台座+アクセントリング */}
      <mesh position={[0, 0.09, 0]} castShadow receiveShadow>
        <cylinderGeometry args={[0.85, 0.95, 0.18, 32]} />
        <meshStandardMaterial color="#1c2833" metalness={0.7} roughness={0.3} />
      </mesh>
      <mesh position={[0, 0.185, 0]}>
        <cylinderGeometry args={[0.87, 0.87, 0.012, 32]} />
        <meshBasicMaterial color={accent} />
      </mesh>
      {/* スーツ — rotateVRM0後の自然な向き(ローカル+z=中央側)で立つ */}
      <group position={[0, 0.19, 0]} rotation={[0, SUIT_FACING, 0]}>
        {vrm && <primitive object={vrm.scene} />}
      </group>
      <TextPlate
        lines={[entry.code, entry.intent ?? entry.blueprint_id ?? '']}
        position={[0, 2.5, 0.4]}
        width={1.7}
        accent={accent}
      />
      {/* [蒸着] その場でヘンシンモーション */}
      <Interactable
        id={`alcove-henshin-${entry.code}`}
        onInteract={() => setTick((t) => t + 1)}
        interactionText="蒸着!"
        enabled={!!vrm && !!vrma}
      >
        <group position={[0.75, 0, 0.6]}>
          <mesh position={[0, 0.3, 0]} castShadow>
            <cylinderGeometry args={[0.06, 0.08, 0.6, 10]} />
            <meshStandardMaterial color="#1c2833" metalness={0.6} roughness={0.4} />
          </mesh>
          <mesh position={[0, 0.66, 0]}>
            <sphereGeometry args={[0.1, 20, 14]} />
            <meshStandardMaterial
              color="#c0392b" emissive="#ff2200" emissiveIntensity={0.8}
            />
          </mesh>
        </group>
      </Interactable>
      {/* [召喚] 中央台へ呼ぶ */}
      <Interactable
        id={`alcove-summon-${entry.code}`}
        onInteract={() => onSummon(entry.code)}
        interactionText={`${entry.code} を中央へ召喚`}
        enabled={!!vrm}
      >
        <group position={[-0.75, 0, 0.6]}>
          <mesh position={[0, 0.3, 0]} castShadow>
            <cylinderGeometry args={[0.06, 0.08, 0.6, 10]} />
            <meshStandardMaterial color="#1c2833" metalness={0.6} roughness={0.4} />
          </mesh>
          <mesh position={[0, 0.66, 0]}>
            <boxGeometry args={[0.16, 0.16, 0.16]} />
            <meshStandardMaterial
              color="#1d5f8a" emissive="#38d9f1" emissiveIntensity={0.7}
            />
          </mesh>
        </group>
      </Interactable>
    </group>
  )
}
