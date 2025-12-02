# 脚本工具说明

本目录包含项目的各类脚本工具。

## 目录结构

### 📰 daily_news/
每日新闻生成相关脚本：
- `generate_daily_news.py` - 主要的新闻生成脚本
- `daily_news_cron.py` - 定时任务版本
- `run_daily_news.sh` - Shell 执行脚本

详见：[daily_news/README.md](daily_news/README.md)

### 🧪 tests/
测试脚本集合：
- `test_ddgs_serper.py` - DDGS 和 Serper 搜索测试
- `test_llm.py` - 大语言模型测试
- `test_news_api.py` - 新闻 API 测试
- `test_qiniu_streamlit.py` - 七牛云集成测试
- `test_serper_search.py` - Serper 搜索测试
- `test_time_filter.py` - 时间过滤测试
- `test_wechat_oauth.py` - 微信 OAuth 测试

### 🔧 tools/
工具脚本：
- `verify_news_fix.py` - 验证新闻修复

## 使用方法

### 运行测试
```bash
cd scripts/tests
python test_llm.py
```

### 生成每日新闻
```bash
cd scripts/daily_news
./run_daily_news.sh
```

## 开发建议

- 新的测试脚本放入 `tests/` 目录
- 功能脚本按类型分类存放
- 每个子目录添加独立的 README.md
