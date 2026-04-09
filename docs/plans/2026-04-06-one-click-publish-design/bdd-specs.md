# BDD Specifications: 一键发布功能

## Feature: 历史文章一键发布到多平台

### Scenario 1: 用户打开发布弹窗
```gherkin
Given 用户在历史记录页面
And 存在已完成的文章
When 用户点击文章卡片上的「发布」按钮
Then 弹出 PublishModal 弹窗
And 弹窗标题显示文章标题
And 显示 7 个平台的复选框列表
And 默认不选中任何平台
```

### Scenario 2: 选择平台并复制内容
```gherkin
Given 发布弹窗已打开
When 用户勾选「微信公众号」
Then 该平台行显示「复制HTML」按钮和「打开发布页」按钮
When 用户点击「复制HTML」
Then 系统调用后端 /api/v1/articles/convert/platform 转换为微信格式
And 转换后的 HTML 内容写入剪贴板（rich_text 格式）
And 显示复制成功提示
```

### Scenario 3: 打开平台发布页
```gherkin
Given 发布弹窗已打开且已勾选平台
When 用户点击某平台的「打开发布页」按钮
Then 在新标签页中打开该平台的发布页 URL
```

### Scenario 4: 复制标题
```gherkin
Given 发布弹窗已打开
When 用户点击底部「复制标题」按钮
Then 文章标题被复制到剪贴板
And 显示「标题已复制」提示
```

### Scenario 5: 全部打开
```gherkin
Given 发布弹窗已打开
And 用户已勾选 3 个平台
When 用户点击「全部打开」按钮
Then 为每个选中的平台在新标签页打开对应发布页 URL
```

### Scenario 6: CSDN 平台格式转换
```gherkin
Given 一篇 Markdown 格式的文章
When 用户选择 CSDN 平台并点击「复制MD」
Then 系统调用后端转换为 CSDN 格式（h1→h2，添加分类标签）
And 转换后的 Markdown 写入剪贴板（plain_text 格式）
```

### Scenario 7: 百家号平台格式转换
```gherkin
Given 一篇 Markdown 格式的文章
When 用户选择百家号平台并点击「复制HTML」
Then 系统调用后端转换为百家号格式（HTML 短段落样式）
And 转换后的 HTML 写入剪贴板（rich_text 格式）
```

### Scenario 8: 知识星球格式转换
```gherkin
Given 一篇 Markdown 格式的文章
When 用户选择知识星球平台并点击「复制MD」
Then 系统调用后端返回原始 Markdown
And 内容写入剪贴板（plain_text 格式）
```

### Scenario 9: 关闭弹窗
```gherkin
Given 发布弹窗已打开
When 用户点击关闭按钮或弹窗外部区域
Then 弹窗关闭
And 不影响历史页面状态
```

### Scenario 10: 格式转换失败
```gherkin
Given 发布弹窗已打开
When 用户点击某平台的复制按钮
And 后端转换接口返回错误
Then 显示「格式转换失败，请重试」错误提示
And 不写入剪贴板
```

### Scenario 11: 剪贴板权限被拒绝
```gherkin
Given 发布弹窗已打开
When 用户点击复制按钮
And 浏览器拒绝剪贴板写入权限
Then 显示「剪贴板访问被拒绝，请检查浏览器权限」错误提示
```

## Testing Strategy

- **Unit tests**: 后端 `platform_converter.py` 新增转换函数测试
- **Component tests**: `PublishModal` 组件渲染和交互测试
- **Integration tests**: 前端调用 `/convert/platform` 的端到端测试
- **Manual QA**: 各平台复制内容粘贴到实际编辑器验证格式正确性
