import './globals.css';
import UiSound from './ui-sound';

export const metadata = {
  title: '蒸着執行録 — GAVAI HENSHIN',
  description: '言葉から鍛造された鎧を、呼出符で召喚する',
  robots: { index: false, follow: false },  // 呼出符入りURLを検索に載せない
};

export default function RootLayout({ children }) {
  return (
    <html lang="ja">
      <body style={{
        margin: 0,
        color: '#dce8f2',
        fontFamily: '"Segoe UI", "Hiragino Sans", "Noto Sans JP", sans-serif',
      }}>
        <UiSound />
        {children}
      </body>
    </html>
  );
}
