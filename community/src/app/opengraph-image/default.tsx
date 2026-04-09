import { ImageResponse } from 'next/og'

export const size = {
  width: 1200,
  height: 630,
}

export const contentType = 'image/png'

export default function ogImage() {
  return new ImageResponse(
    (
      <div
        style={{
          fontSize: 128,
          background: 'linear-gradient(to bottom right, #DC2626, #991B1B)',
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div style={{
            width: '80px',
            height: '80px',
            background: 'white',
            borderRadius: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#DC2626',
            fontSize: '48px',
            fontWeight: 'bold'
          }}>
            超
          </div>
          <span style={{ fontSize: '64px', fontWeight: 'bold' }}>超能写手</span>
        </div>
        <p style={{ fontSize: '32px', marginTop: '20px', opacity: 0.9 }}>
          AI 驱动的创作社区
        </p>
      </div>
    ),
    {
      ...size,
    }
  )
}
