export const metadata = {
  title: '蒸着執行録 — GAVAI HENSHIN',
  description: '言葉から鍛造された鎧を、呼出符で召喚する',
};

export default function RootLayout({ children }) {
  return (
    <html lang="ja">
      <body style={{
        margin: 0,
        background: '#04080d',
        color: '#dce8f2',
        fontFamily: '"Segoe UI", "Hiragino Sans", "Noto Sans JP", sans-serif',
      }}>
        {children}
      </body>
    </html>
  );
}
