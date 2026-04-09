import { NextAuthOptions } from "next-auth"
import GoogleProvider from "next-auth/providers/google"
import { getInternalApiUrl } from "@/lib/server-backend-url"

export const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID || "",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET || "",
      httpOptions: {
        timeout: 10000, // 增加超时时间到 10 秒
      },
    }),
  ],
  callbacks: {
    async jwt({ token, account, profile }) {
      if (account && profile) {
        // 调用后端 API 获取 JWT token
        try {
          const apiUrl = getInternalApiUrl()
          const response = await fetch(`${apiUrl}/api/v1/auth/exchange-token`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              google_id: profile.sub,
              email: profile.email,
              name: profile.name,
              // @ts-ignore - picture exists on Google profile
              picture: profile.picture
            })
          })
          
          if (response.ok) {
            const data = await response.json()
            token.accessToken = data.access_token
            token.id = data.user.id
            token.email = data.user.email
            token.name = data.user.display_name || data.user.username
            // 兼容 avatar 和 avatar_url 字段
            token.picture = data.user.avatar || data.user.avatar_url
          } else {
            console.error('Failed to get backend JWT token')
            token.accessToken = undefined
          }
        } catch (error) {
          console.error('Error calling backend auth API:', error)
          token.accessToken = undefined
        }

        token.id = token.id || profile.sub
        token.email = token.email || profile.email
        token.name = token.name || profile.name
        // @ts-ignore
        token.picture = token.picture || profile.picture
      }
      return token
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.id as string
        session.user.email = token.email as string
        session.user.name = token.name as string
        session.user.image = token.picture as string
      }
      // @ts-ignore
      session.accessToken = token.accessToken as string
      return session
    },
    async redirect({ url, baseUrl }) {
      if (url.startsWith(baseUrl)) return url
      else if (url.startsWith("/")) return `${baseUrl}${url}`
      return baseUrl + "/workspace"
    },
  },
  pages: {
    signIn: '/auth/signin',
    error: '/auth/error',
  },
  session: {
    strategy: "jwt",
    maxAge: 30 * 24 * 60 * 60,
  },
  secret: process.env.NEXTAUTH_SECRET,
}
