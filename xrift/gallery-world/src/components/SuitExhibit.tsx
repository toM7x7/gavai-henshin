import { useEffect, useRef, useState } from 'react'
import { useFrame } from '@react-three/fiber'
import { Group } from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { VRMLoaderPlugin, VRMUtils, type VRM } from '@pixiv/three-vrm'
import { fetchSuitVrmUrl, type GalleryEntry } from '~/lib/gallery'
import { TextPlate } from './TextPlate'

interface SuitExhibitProps {
  entry: GalleryEntry
  position: [number, number, number]
  onResult: (line: string) => void
}

// 展示台1基 = スーツVRMを外部URLから実行時ロードして立たせる。
// 成否はStatusBoardへ報告する(このワールドは計測器を兼ねる)
export function SuitExhibit({ entry, position, onResult }: SuitExhibitProps) {
  const [vrm, setVrm] = useState<VRM | null>(null)
  const spinRef = useRef<Group>(null)

  useEffect(() => {
    let disposed = false
    ;(async () => {
      try {
        const url = await fetchSuitVrmUrl(entry.code)
        const loader = new GLTFLoader()
        loader.register((parser) => new VRMLoaderPlugin(parser))
        const gltf = await loader.loadAsync(url)
        const loaded = gltf.userData.vrm as VRM
        VRMUtils.rotateVRM0(loaded)
        if (disposed) return
        setVrm(loaded)
        onResult(`✓ ${entry.code} VRM表示成功`)
      } catch (e) {
        onResult(`✗ ${entry.code} ${String((e as Error)?.message ?? e)}`)
      }
    })()
    return () => {
      disposed = true
    }
    // 展示は符号ごとに一度だけロードする
  }, [entry.code])

  useFrame((_, dt) => {
    if (spinRef.current) spinRef.current.rotation.y += dt * 0.35
    vrm?.update(dt)
  })

  const accent = entry.palette?.emissive ?? entry.palette?.accent ?? '#9fdcff'

  return (
    <group position={position}>
      <mesh position={[0, 0.1, 0]} castShadow receiveShadow>
        <cylinderGeometry args={[0.85, 0.95, 0.2, 32]} />
        <meshStandardMaterial color="#233240" metalness={0.6} roughness={0.35} />
      </mesh>
      <mesh position={[0, 0.205, 0]}>
        <cylinderGeometry args={[0.86, 0.86, 0.012, 32]} />
        <meshBasicMaterial color={accent} />
      </mesh>
      <group ref={spinRef} position={[0, 0.21, 0]}>
        {vrm && <primitive object={vrm.scene} />}
      </group>
      <TextPlate
        lines={[entry.code, entry.intent ?? entry.blueprint_id ?? '']}
        position={[0, 2.35, 0]}
        width={1.9}
        accent={accent}
      />
    </group>
  )
}
