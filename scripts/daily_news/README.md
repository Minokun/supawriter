# 每日新闻生成脚本使用说明

## 📋 脚本说明

本目录包含用于生成每日AI新闻的脚本，可以自动从机器之心和站长之家获取最新新闻并生成公众号文章格式。

## 📁 文件结构

```
scripts/
├── generate_daily_news.py    # 主要的新闻生成脚本
├── daily_news_cron.py       # 定时任务版本（适用于cron）
├── run_daily_news.sh        # Shell执行脚本
└── README_DAILY_NEWS.md     # 本说明文件
```

## 🚀 使用方法

### 方法1：直接运行Python脚本

```bash
cd /Users/wxk/Desktop/workspace/supawriter
python3 scripts/generate_daily_news.py
```

### 方法2：使用Shell脚本

```bash
cd /Users/wxk/Desktop/workspace/supawriter/scripts
./run_daily_news.sh
```

### 方法3：设置定时任务

编辑crontab：
```bash
crontab -e
```

添加以下行（每天早上8点执行）：
```bash
0 8 * * * cd /Users/wxk/Desktop/workspace/supawriter && python3 scripts/daily_news_cron.py
```

## 📊 功能特性

### 数据源
- **机器之心API**: 获取专业AI技术资讯
- **站长之家API**: 获取实时AI行业新闻

### 内容筛选
- 自动筛选昨天到今天的新闻
- 机器之心：获取最新50篇文章，筛选24小时内发布的
- 站长之家：获取最新20条实时新闻

### 输出格式
- **格式**: Markdown格式，适合公众号发布
- **内容**: 包含标题、图片、摘要、发布时间
- **结构**: 分为"AI专题新闻"和"实时新闻"两个部分

### 文件保存
- **路径**: `/Users/wxk/Desktop/workspace/supawriter/data/daily_news/`
- **命名**: `AI新闻快速总览_YYYYMMDD.md`
- **编码**: UTF-8

## 📝 输出示例

生成的文章包含以下结构：

```markdown
# AI新闻快速总览 - 2025年11月11日

> **每日AI资讯精选**  
> 汇聚最新AI技术动态、行业资讯和前沿研究  

## 🤖 AI专题新闻

### 标题1
![图片](图片链接)
摘要内容...
**发布时间：** 2025-11-11 10:30

## 📰 实时新闻

### 标题2
![图片](图片链接)
新闻内容...
**发布时间：** 最新

## 📊 今日数据统计
- **AI专题新闻：** X 篇
- **实时新闻：** X 条
```

## 🔧 配置说明

### API接口
- **机器之心**: `https://www.jiqizhixin.com/api/article_library/articles.json`
- **站长之家**: `https://app.chinaz.com/djflkdsoisknfoklsyhownfrlewfknoiaewf/ai/GetAiInfoList.aspx`

### 请求参数
- 机器之心：`sort=time&page=1&per=50`
- 站长之家：`flag=zh_cn&type=1&page=1&pagesize=50`

### 时间筛选
- 机器之心：根据`publishedAt`字段筛选昨天到今天的文章
- 站长之家：取最新20条（API不支持时间筛选）

## 🐛 故障排除

### 常见问题

1. **网络连接失败**
   - 检查网络连接
   - 确认API接口可访问

2. **权限错误**
   - 确保脚本有执行权限：`chmod +x run_daily_news.sh`
   - 确保输出目录有写入权限

3. **Python环境问题**
   - 确保安装了`requests`库：`pip install requests`
   - 检查Python版本（建议3.7+）

4. **文件保存失败**
   - 检查输出目录是否存在
   - 确保有足够的磁盘空间

### 日志查看

定时任务版本会生成日志文件：
```bash
tail -f /Users/wxk/Desktop/workspace/supawriter/logs/daily_news.log
```

## 📅 定时任务建议

### 推荐执行时间
- **每日8:00**: 获取前一天晚上到当天早上的新闻
- **每日18:00**: 获取当天的新闻更新

### Crontab示例
```bash
# 每天早上8点生成每日新闻
0 8 * * * cd /Users/wxk/Desktop/workspace/supawriter && python3 scripts/daily_news_cron.py

# 每天下午6点更新新闻
0 18 * * * cd /Users/wxk/Desktop/workspace/supawriter && python3 scripts/daily_news_cron.py
```

## 🔄 版本更新

如需修改脚本功能：

1. **修改数据源**: 编辑`generate_daily_news.py`中的API URL
2. **调整筛选条件**: 修改时间筛选逻辑
3. **更改输出格式**: 调整markdown模板
4. **添加新的数据源**: 参考现有的fetch函数添加新的API

## 📞 技术支持

如遇到问题，请检查：
1. 网络连接状态
2. API接口可用性
3. Python环境和依赖
4. 文件权限设置

---

*最后更新：2025-11-11*
