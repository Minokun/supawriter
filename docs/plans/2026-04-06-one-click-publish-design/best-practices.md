# Best Practices: 一键发布功能

## Security

- 平台发布页 URL 使用常量定义，不接受用户输入，防止开放重定向
- 剪贴板操作在用户点击事件中触发（浏览器安全策略要求）
- 后端转换接口已有认证中间件保护

## Performance

- PublishModal 使用 `dynamic()` 延迟加载，不增加首屏包体积
- 格式转换调用后端，利用现有 debounce 逻辑避免重复请求
- 可考虑对转换结果做前端缓存（localStorage，1小时过期，复用 SplitEditor 模式）

## UX

- 复制操作必须有明确的成功/失败反馈（Toast 提示）
- 「全部打开」可能触发多个新标签页，需提前告知用户允许弹窗
- 每个平台行显示对应的内容格式标签（HTML/MD/文本），让用户知道复制的是什么格式
- 弹窗支持 ESC 键关闭
- 复制按钮点击后短暂变为「已复制」状态

## Code Quality

- 平台配置集中在 `PLATFORMS` 常量，便于后续扩展
- 转换逻辑复用现有 `platform_converter.py`，不重复实现
- 前端复用现有 `clipboard.ts` 工具函数
- 遵循现有组件命名和目录结构约定
