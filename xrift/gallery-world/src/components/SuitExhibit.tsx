import { useEffect, useRef, useState } from 'react'
import { useFrame } from '@react-three/fiber'
import { Group } from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { VRMLoaderPlugin, VRMUtils, type VRM } from '@pixiv/three-vrm'
import { VRMAnimationLoaderPlugin, type VRMAnimation } from '@pixiv/three-vrm-animation'
import { enqueueLoad, fetchSuitFiles, type GalleryEntry } from '~/lib/gallery'
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
        onResult?.(`✓ ${code} 展示中`)
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

interface AlcoveExhibitProps {
  entry: GalleryEntry
  position: [number, number, number]
  rotationY: number
  onResult: (line: string) => void
}

// 格納庫の壁面アルコーブ1基(アイアンマン格納庫の意匠):
// 背光フレーム+台座+スーツ+符号プレート
export function AlcoveExhibit({ entry, position, rotationY, onResult }: AlcoveExhibitProps) {
  const { vrm } = useSuit(entry.code, false, onResult)
  const spinRef = useRef<Group>(null)

  useFrame((_, dt) => {
    if (spinRef.current) spinRef.current.rotation.y += dt * 0.25
    vrm?.update(dt)
  })

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
      <group ref={spinRef} position={[0, 0.19, 0]}>
        {vrm && <primitive object={vrm.scene} />}
      </group>
      <TextPlate
        lines={[entry.code, entry.intent ?? entry.blueprint_id ?? '']}
        position={[0, 2.5, 0.4]}
        width={1.7}
        accent={accent}
      />
    </group>
  )
}
