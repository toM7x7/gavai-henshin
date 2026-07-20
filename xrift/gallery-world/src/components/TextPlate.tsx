import { useMemo } from 'react'
import { CanvasTexture, SRGBColorSpace } from 'three'

interface TextPlateProps {
  lines: string[]
  position?: [number, number, number]
  rotation?: [number, number, number]
  width?: number
  accent?: string
}

// フォント読込に依存しないcanvasテクスチャの表示板。
// 検証ワールドの「計器」— 接続結果をワールド内で読めることが目的
export function TextPlate({
  lines,
  position = [0, 0, 0],
  rotation = [0, 0, 0],
  width = 3,
  accent = '#9fdcff',
}: TextPlateProps) {
  const texture = useMemo(() => {
    const can = document.createElement('canvas')
    can.width = 1024
    can.height = 512
    const g = can.getContext('2d')!
    g.fillStyle = 'rgba(6, 12, 18, 0.94)'
    g.fillRect(0, 0, can.width, can.height)
    g.strokeStyle = accent
    g.lineWidth = 4
    g.strokeRect(10, 10, can.width - 20, can.height - 20)
    g.textBaseline = 'top'
    lines.forEach((line, i) => {
      g.fillStyle = i === 0 ? accent : '#dce8f2'
      g.font = i === 0
        ? 'bold 52px "Segoe UI", "Hiragino Sans", sans-serif'
        : '40px "Segoe UI", "Hiragino Sans", sans-serif'
      g.fillText(line, 44, 44 + i * 78, can.width - 88)
    })
    const tex = new CanvasTexture(can)
    tex.colorSpace = SRGBColorSpace
    return tex
    // 行内容が変わった時だけ描き直す
  }, [lines.join('\n'), accent])

  return (
    <mesh position={position} rotation={rotation}>
      <planeGeometry args={[width, width / 2]} />
      <meshBasicMaterial map={texture} transparent />
    </mesh>
  )
}
