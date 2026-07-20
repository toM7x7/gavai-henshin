import { useMemo } from 'react'
import { CanvasTexture, SRGBColorSpace } from 'three'

interface TextPlateProps {
  lines: string[]
  position?: [number, number, number]
  rotation?: [number, number, number]
  width?: number
  accent?: string
  /** 横:縦の比。2=情報板(既定)、5=カタログ行のような細長プレート */
  aspect?: number
}

// フォント読込に依存しないcanvasテクスチャの表示板
export function TextPlate({
  lines,
  position = [0, 0, 0],
  rotation = [0, 0, 0],
  width = 3,
  accent = '#9fdcff',
  aspect = 2,
}: TextPlateProps) {
  const texture = useMemo(() => {
    const canW = 1024
    const canH = Math.max(128, Math.round(1024 / aspect))
    const can = document.createElement('canvas')
    can.width = canW
    can.height = canH
    const g = can.getContext('2d')!
    g.fillStyle = 'rgba(6, 12, 18, 0.94)'
    g.fillRect(0, 0, canW, canH)
    g.strokeStyle = accent
    g.lineWidth = 4
    g.strokeRect(8, 8, canW - 16, canH - 16)
    if (lines.length === 1) {
      // 一行プレート: 中央寄せの大きな文字
      g.fillStyle = accent
      g.font = `bold ${Math.round(canH * 0.5)}px "Segoe UI", "Hiragino Sans", sans-serif`
      g.textAlign = 'center'
      g.textBaseline = 'middle'
      g.fillText(lines[0], canW / 2, canH / 2 + 4, canW - 60)
    } else {
      g.textBaseline = 'top'
      const step = Math.min(78, Math.round((canH - 88) / Math.max(1, lines.length)))
      lines.forEach((line, i) => {
        g.fillStyle = i === 0 ? accent : '#dce8f2'
        g.font = i === 0
          ? `bold ${Math.min(52, step - 10)}px "Segoe UI", "Hiragino Sans", sans-serif`
          : `${Math.min(40, step - 18)}px "Segoe UI", "Hiragino Sans", sans-serif`
        g.fillText(line, 44, 44 + i * step, canW - 88)
      })
    }
    const tex = new CanvasTexture(can)
    tex.colorSpace = SRGBColorSpace
    return tex
    // 行内容が変わった時だけ描き直す
  }, [lines.join('\n'), accent, aspect])

  return (
    <mesh position={position} rotation={rotation}>
      <planeGeometry args={[width, width / aspect]} />
      <meshBasicMaterial map={texture} transparent />
    </mesh>
  )
}
