import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@store/authStore'

// Pages
import Login from '@pages/auth/Login'
import Workspace from '@pages/workspace/Workspace'
import Writer from '@pages/writer/Writer'
import AIChat from '@pages/ai-chat/AIChat'
import Inspiration from '@pages/inspiration/Inspiration'
import History from '@pages/history/History'
import News from '@pages/news/News'
import TweetTopics from '@pages/tweet-topics/TweetTopics'
import Rewrite from '@pages/rewrite/Rewrite'
import Settings from '@pages/settings/Settings'

// 布局组件
import MainLayout from '@components/layout/MainLayout'

// 路由守卫
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, user } = useAuthStore()

  if (!token || !user) {
    return <Navigate to="/auth/login" replace />
  }

  return <>{children}</>
}

// 公共路由（不需要登录）
function PublicRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuthStore()

  if (token) {
    return <Navigate to="/workspace" replace />
  }

  return <>{children}</>
}

function App() {
  return (
    <Router>
      <Routes>
        {/* 认证页面 */}
        <Route
          path="/auth/login"
          element={
            <PublicRoute>
              <Login />
            </PublicRoute>
          }
        />

        {/* OAuth 回调 */}
        <Route path="/auth/callback" element={<div>Processing...</div>} />

        {/* 主应用（需要登录） */}
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <MainLayout />
            </ProtectedRoute>
          }
        >
          {/* 默认重定向到工作台 */}
          <Route index element={<Navigate to="/workspace" replace />} />

          {/* 工作台 */}
          <Route path="workspace" element={<Workspace />} />

          {/* 超能写手 */}
          <Route path="writer" element={<Writer />} />

          {/* AI 助手 */}
          <Route path="ai-chat" element={<AIChat />} />

          {/* 灵感发现 */}
          <Route path="inspiration" element={<Inspiration />} />

          {/* 历史记录 */}
          <Route path="history" element={<History />} />

          {/* 新闻资讯 */}
          <Route path="news" element={<News />} />

          {/* 推文选题 */}
          <Route path="tweet-topics" element={<TweetTopics />} />

          {/* 文章再创作 */}
          <Route path="rewrite" element={<Rewrite />} />

          {/* 系统设置 */}
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </Router>
  )
}

export default App
