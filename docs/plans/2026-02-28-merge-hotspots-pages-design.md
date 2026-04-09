# 热点页面合并设计

## 背景
- `/hotspots` (热点中心) 和 `/inspiration` (全网热点) 功能重复
- 热点中心功能更完善，但缺少自动刷新
- 全网热点有 5 分钟自动刷新功能

## 方案
保留热点中心，移除全网热点，将自动刷新功能加入热点中心。

## 变更内容

### 1. 热点中心添加自动刷新
- 添加 5 分钟自动刷新定时器
- 添加自动刷新开关（默认开启）
- 显示下次刷新倒计时

### 2. 移除全网热点页面
- 删除 `/frontend/src/app/inspiration/` 目录

### 3. 更新导航菜单
- 从 Navigation.tsx 移除 "全网热点" 入口
- 热点资讯下保留：热点中心、新闻资讯

## 影响范围
- `frontend/src/app/hotspots/page.tsx` - 添加自动刷新
- `frontend/src/app/inspiration/` - 删除
- `frontend/src/components/layout/Navigation.tsx` - 移除菜单项
