# SupaWriter API SDK

TypeScript SDK for SupaWriter API integration.

## 安装

SDK 已包含在项目中，无需额外安装。

## 配置

在 `.env.local` 中配置 API 地址：

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 使用示例

### 1. 系统设置 API

```typescript
import { apiClient, settingsApi } from '@/lib/api';

// 设置认证 token
apiClient.setToken('your-jwt-token');

// 获取 API 密钥列表
const { keys } = await settingsApi.getApiKeys();

// 创建 API 密钥
await settingsApi.createApiKey({
  provider: 'openai',
  api_key: 'sk-...',
  is_active: true
});

// 删除 API 密钥
await settingsApi.deleteApiKey('openai');

// 获取模型配置
const config = await settingsApi.getModelConfig();

// 更新模型配置
await settingsApi.updateModelConfig({
  chat_model: {
    provider: 'openai',
    model_name: 'gpt-4',
    temperature: 0.7
  }
});

// 获取用户偏好
const preferences = await settingsApi.getPreferences();

// 更新用户偏好
await settingsApi.updatePreferences({
  editor_theme: 'dark',
  language: 'zh-CN',
  auto_save: true
});
```

### 2. 文章生成 API（SSE 流式）

```typescript
import { articlesApi } from '@/lib/api';

// 流式生成文章
const eventSource = articlesApi.generateArticleStream(
  {
    topic: '人工智能的未来发展',
    model_type: 'deepseek',
    model_name: 'deepseek-chat'
  },
  (event) => {
    console.log('Progress:', event.progress_percent);
    console.log('Step:', event.current_step);
    
    if (event.type === 'completed') {
      console.log('Content:', event.data?.content);
    }
  },
  (error) => {
    console.error('Error:', error);
  }
);

// 取消生成
// eventSource.close();

// 查询进度
const progress = await articlesApi.getProgress('article-id');

// 获取队列
const { items, total } = await articlesApi.getQueue(20);

// 从队列移除
await articlesApi.removeFromQueue('article-id');
```

### 3. 热点数据 API

```typescript
import { hotspotsApi } from '@/lib/api';

// 获取热点源列表
const { sources } = await hotspotsApi.getSources();

// 获取热点数据
const { data, from_cache } = await hotspotsApi.getHotspots('baidu');

// 遍历热点
data.forEach(item => {
  console.log(item.title, item.url);
});
```

## React 组件示例

### 文章生成组件

```typescript
'use client';

import { useState } from 'react';
import { articlesApi, type ProgressEvent } from '@/lib/api';

export default function ArticleGenerator() {
  const [topic, setTopic] = useState('');
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [content, setContent] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerate = () => {
    setIsGenerating(true);
    setProgress(0);
    setContent('');

    const eventSource = articlesApi.generateArticleStream(
      { topic },
      (event: ProgressEvent) => {
        setProgress(event.progress_percent);
        setCurrentStep(event.current_step);

        if (event.type === 'completed' && event.data?.content) {
          setContent(event.data.content);
          setIsGenerating(false);
        } else if (event.type === 'error') {
          console.error(event.error_message);
          setIsGenerating(false);
        }
      },
      (error) => {
        console.error(error);
        setIsGenerating(false);
      }
    );
  };

  return (
    <div className="space-y-4">
      <input
        type="text"
        value={topic}
        onChange={(e) => setTopic(e.target.value)}
        placeholder="输入文章主题"
        className="w-full px-4 py-2 border rounded"
      />
      
      <button
        onClick={handleGenerate}
        disabled={isGenerating || !topic}
        className="px-6 py-2 bg-blue-500 text-white rounded"
      >
        {isGenerating ? '生成中...' : '开始生成'}
      </button>

      {isGenerating && (
        <div className="space-y-2">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-500 h-2 rounded-full transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-sm text-gray-600">{currentStep}</p>
        </div>
      )}

      {content && (
        <div className="mt-4 p-4 border rounded">
          <pre className="whitespace-pre-wrap">{content}</pre>
        </div>
      )}
    </div>
  );
}
```

### 热点列表组件

```typescript
'use client';

import { useState, useEffect } from 'react';
import { hotspotsApi, type HotspotItem } from '@/lib/api';

export default function HotspotsList() {
  const [source, setSource] = useState('baidu');
  const [hotspots, setHotspots] = useState<HotspotItem[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadHotspots();
  }, [source]);

  const loadHotspots = async () => {
    setLoading(true);
    try {
      const { data } = await hotspotsApi.getHotspots(source);
      setHotspots(data);
    } catch (error) {
      console.error('Failed to load hotspots:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <select
        value={source}
        onChange={(e) => setSource(e.target.value)}
        className="px-4 py-2 border rounded"
      >
        <option value="baidu">百度热搜</option>
        <option value="weibo">微博热搜</option>
        <option value="douyin">抖音热搜</option>
        <option value="thepaper">澎湃新闻</option>
        <option value="36kr">36氪</option>
      </select>

      {loading ? (
        <p>加载中...</p>
      ) : (
        <ul className="space-y-2">
          {hotspots.map((item, index) => (
            <li key={index} className="p-3 border rounded hover:bg-gray-50">
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline"
              >
                {item.title}
              </a>
              {item.hot_score && (
                <span className="ml-2 text-sm text-red-500">
                  🔥 {item.hot_score}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

## API 参考

### ApiClient

基础 HTTP 客户端。

```typescript
class ApiClient {
  setToken(token: string): void;
  clearToken(): void;
  get<T>(endpoint: string): Promise<T>;
  post<T>(endpoint: string, data?: any): Promise<T>;
  put<T>(endpoint: string, data?: any): Promise<T>;
  delete<T>(endpoint: string): Promise<T>;
  createEventSource(endpoint: string, onMessage, onError?): EventSource;
}
```

### SettingsApi

系统设置相关 API。

- `getApiKeys()` - 获取 API 密钥列表
- `createApiKey(data)` - 创建 API 密钥
- `deleteApiKey(provider)` - 删除 API 密钥
- `getModelConfig()` - 获取模型配置
- `updateModelConfig(data)` - 更新模型配置
- `getPreferences()` - 获取用户偏好
- `updatePreferences(data)` - 更新用户偏好

### ArticlesApi

文章生成相关 API。

- `generateArticleStream(request, onProgress, onError)` - 流式生成文章
- `getProgress(articleId)` - 查询生成进度
- `getQueue(limit)` - 获取用户队列
- `removeFromQueue(articleId)` - 从队列移除

### HotspotsApi

热点数据相关 API。

- `getHotspots(source)` - 获取热点数据
- `getSources()` - 获取热点源列表

## 错误处理

```typescript
try {
  const data = await settingsApi.getApiKeys();
} catch (error) {
  if (error instanceof Error) {
    console.error('Error:', error.message);
  }
}
```

## TypeScript 类型

所有 API 响应都有完整的 TypeScript 类型定义，IDE 会提供自动补全和类型检查。

## 注意事项

1. 使用前需要调用 `apiClient.setToken()` 设置认证 token
2. SSE 连接需要手动关闭：`eventSource.close()`
3. 所有 API 调用都是异步的，需要使用 `await` 或 `.then()`
4. 建议在组件卸载时清理 EventSource 连接

## 开发建议

- 使用 React Query 或 SWR 管理 API 状态
- 实现全局错误处理和重试机制
- 添加请求拦截器处理认证过期
- 使用 TypeScript 严格模式确保类型安全
