# Architecture: 一键发布功能

## Component Overview

```
┌─────────────────────────────────────────────┐
│  History Page (page.tsx)                     │
│                                              │
│  ┌─── Article Card ───────────────────────┐  │
│  │  [Download] [Edit] [Publish] [Delete]  │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  ┌─── PublishModal ──────────────────────┐   │
│  │  Platform: ☑ wechat   [Copy] [Open]   │   │
│  │  Platform: ☑ zhihu    [Copy] [Open]   │   │
│  │  Platform: ☐ xiaohongshu [Copy] [Open]│   │
│  │  Platform: ☑ csdn     [Copy] [Open]   │   │
│  │  Platform: ☐ baijiahao [Copy] [Open]  │   │
│  │  Platform: ☐ zsxq     [Copy] [Open]   │   │
│  │  Platform: ☐ toutiao  [Copy] [Open]   │   │
│  │                                        │   │
│  │  [Copy Title]  [Open All Selected]     │   │
│  └────────────────────────────────────────┘   │
└──────────────────────────────────────────────┘
         │
         │ POST /api/v1/articles/convert/platform
         ▼
┌─────────────────────────────────────────────┐
│  Backend: articles_enhanced.py               │
│  → platform_converter.convert_to_platform()  │
│    → _convert_wechat / _convert_csdn / ...   │
└─────────────────────────────────────────────┘
```

## File Changes

### Backend (2 files)

| File | Change |
|------|--------|
| `utils/platform_converter.py` | Add `_convert_csdn()`, `_convert_baijiahao()`, `_convert_zsxq()`, update `SUPPORTED_PLATFORMS` and `convert_to_platform()` |
| `backend/api/routes/articles_enhanced.py` | No change needed — existing `/convert/platform` endpoint handles new platforms automatically |

### Frontend (2 files)

| File | Change |
|------|--------|
| `frontend/src/components/writer/PublishModal.tsx` | **New file** — PublishModal component with platform selection, copy, and open functionality |
| `frontend/src/app/history/page.tsx` | Add publish button to article cards, add PublishModal state and rendering |

### Types (1 file)

| File | Change |
|------|--------|
| `frontend/src/types/api.ts` | Extend `PlatformType` to include `'csdn' \| 'baijiahao' \| 'zsxq'` |

## Data Flow

1. User clicks "Publish" button on article card → `setPublishArticle(article)`
2. PublishModal opens with article data
3. User selects platform(s)
4. For copy action:
   - Call `historyApi.convertPlatform(article.content, platform, article.topic)`
   - Backend converts content via `platform_converter.convert_to_platform()`
   - Frontend receives `{content, format, copy_format}`
   - Use `copyRichTextToClipboard()` or `navigator.clipboard.writeText()` based on `copy_format`
5. For open action:
   - `window.open(PLATFORMS[platform].url, '_blank')`

## Platform Configuration

```typescript
const PLATFORMS = {
  wechat:       { name: '微信公众号', url: 'https://mp.weixin.qq.com/', copyFormat: 'rich_text' },
  zhihu:        { name: '知乎', url: 'https://zhuanlan.zhihu.com/write', copyFormat: 'plain_text' },
  xiaohongshu:  { name: '小红书', url: 'https://creator.xiaohongshu.com/publish/publish', copyFormat: 'plain_text' },
  csdn:         { name: 'CSDN', url: 'https://mp.csdn.net/mp_blog/creation/editor', copyFormat: 'plain_text' },
  baijiahao:    { name: '百家号', url: 'https://baijiahao.baidu.com/builder/rc/edit', copyFormat: 'rich_text' },
  zsxq:         { name: '知识星球', url: 'https://wx.zsxq.com/', copyFormat: 'plain_text' },
  toutiao:      { name: '今日头条', url: 'https://mp.toutiao.com/profile_v4/graphic/articles', copyFormat: 'rich_text' },
};
```
