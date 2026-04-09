import { NextRequest, NextResponse } from 'next/server';

interface NewsItem {
  title: string;
  url?: string;
  hot?: string;
  heat?: string;
  hot_score?: string;
  hot_value?: string;
  desc?: string;
  description?: string;
  image?: string;
}

class UpstreamNewsFetchError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = 'UpstreamNewsFetchError';
  }
}

// 后端 API 地址
const BACKEND_API = process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000';

// TrendRadar 支持的源
const TRENDRADAR_SOURCES = [
  'baidu', 'weibo', 'zhihu', 'douyin', 'bilibili',
  'toutiao', 'tieba', 'thepaper', 'ifeng', 'wallstreetcn', 'cls'
];

// 缓存数据，5分钟过期
const cache = new Map<string, { data: NewsItem[]; timestamp: number }>();
const CACHE_TTL = 5 * 60 * 1000; // 5分钟

/**
 * 从后端 TrendRadar API 获取热点数据
 */
async function fetchFromTrendRadar(source: string): Promise<NewsItem[]> {
  try {
    const response = await fetch(`${BACKEND_API}/api/v1/hotspots/v2/latest/${source}?limit=30`, {
      headers: {
        'Content-Type': 'application/json',
      },
      cache: 'no-store',
    });

    if (!response.ok) {
      console.error(`TrendRadar API 返回错误: ${response.status}`);
      return [];
    }

    const data = await response.json();
    const items = data?.items || [];

    // 转换为前端格式
    return items.map((item: any) => ({
      title: item.title || '',
      url: item.url || '',
      desc: item.description || '',
      description: item.description || '',
      hot_score: item.hot_value ? String(item.hot_value) : '',
      hot_value: item.hot_value,
    }));
  } catch (error) {
    console.error(`从 TrendRadar 获取 ${source} 失败:`, error);
    return [];
  }
}

/**
 * 触发后端同步热点数据
 */
async function triggerSync(source: string): Promise<void> {
  try {
    await fetch(`${BACKEND_API}/api/v1/hotspots/v2/sync?source=${source}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });
  } catch (error) {
    console.error(`同步 ${source} 失败:`, error);
  }
}

// ============ 备用：直接爬取（仅在 TrendRadar 不可用时使用） ============

async function fetchBaiduHotFallback(): Promise<NewsItem[]> {
  try {
    const response = await fetch('https://top.baidu.com/board?tab=realtime', {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
      },
      cache: 'no-store',
    });
    const html = await response.text();
    const jsonMatch = html.match(/<!--s-data:(.*?)-->/);
    if (jsonMatch) {
      const data = JSON.parse(jsonMatch[1]);
      const cards = data?.data?.cards || [];
      if (cards.length > 0) {
        const content = cards[0].content || [];
        return content.slice(0, 30).map((item: any) => ({
          title: item.word || '',
          desc: item.desc || '',
          url: item.url || `https://www.baidu.com/s?wd=${encodeURIComponent(item.word || '')}`,
          hot_score: item.hotScore || '',
        }));
      }
    }
  } catch (error) {
    console.error('备用获取百度热搜失败:', error);
  }
  return [];
}

async function fetchWeiboHotFallback(): Promise<NewsItem[]> {
  try {
    const response = await fetch('https://s.weibo.com/top/summary', {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Cookie': 'SUB=_2AkMWJ_fdf8NxqwJRmP8SxWjnaY12yQ_EieKkjrMJJRMxHRl-yT9jqmgbtRB6PO6Nc9vS-pTH2Q7q8lW1D4q4e6P4',
      },
      cache: 'no-store',
    });
    const html = await response.text();
    const pattern = /<a href="(\/weibo\?q=[^"]+)"[^>]*>(.*?)<\/a>.*?<span[^>]*>(.*?)<\/span>/gs;
    const matches = [...html.matchAll(pattern)];
    const seen = new Set<string>();
    const excludeWords = ['首页', '发现', '游戏', '注册', '登录', '帮助', '剧集影响力榜', '综艺影响力榜', '更多'];
    const result: NewsItem[] = [];

    for (const match of matches) {
      const title = match[2].replace(/<[^>]+>/g, '').trim();
      const heat = match[3].replace(/<[^>]+>/g, '').trim();
      if (title && !seen.has(title) && title.length > 2 && !excludeWords.includes(title)) {
        seen.add(title);
        result.push({
          title,
          url: `https://s.weibo.com${match[1]}`,
          heat,
        });
      }
    }
    return result.slice(0, 30);
  } catch (error) {
    console.error('备用获取微博热搜失败:', error);
  }
  return [];
}

async function fetchDouyinHotFallback(): Promise<NewsItem[]> {
  try {
    const response = await fetch('https://www.douyin.com/aweme/v1/web/hot/search/list/?device_platform=webapp&aid=6383&channel=channel_pc_web', {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': 'https://www.douyin.com/',
      },
      cache: 'no-store',
    });
    const data = await response.json();
    const list = data?.data?.word_list || [];
    return list.slice(0, 30).map((item: any) => ({
      title: item.word || '',
      hot_score: item.hot_value ? String(item.hot_value) : '',
      url: `https://www.douyin.com/search/${encodeURIComponent(item.word || '')}`,
    }));
  } catch (error) {
    console.error('备用获取抖音热点失败:', error);
  }
  return [];
}

async function fetchBilibiliHotFallback(): Promise<NewsItem[]> {
  try {
    const response = await fetch('https://api.bilibili.com/x/web-interface/popular?ps=50&pn=1', {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': 'https://www.bilibili.com/',
      },
      cache: 'no-store',
    });
    const data = await response.json();
    if (data?.code === 0 && data?.data?.list) {
      return data.data.list.slice(0, 30).map((item: any) => {
        const view = item?.stat?.view || 0;
        const viewStr = view >= 10000 ? `${(view / 10000).toFixed(1)}万` : String(view);
        return {
          title: item.title || '',
          url: `https://www.bilibili.com/video/${item.bvid}`,
          desc: `UP: ${item?.owner?.name || ''} · ${item.tname || ''} · ▶ ${viewStr}`,
        };
      });
    }
  } catch (error) {
    console.error('备用获取B站热门失败:', error);
  }
  return [];
}

async function fetchZhihuHotFallback(): Promise<NewsItem[]> {
  try {
    const response = await fetch('https://www.zhihu.com/api/v4/search/top_search', {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
      },
      cache: 'no-store',
    });
    const data = await response.json();
    const words = data?.top_search?.words || [];
    return words.slice(0, 30).map((item: any) => ({
      title: item.display_query || item.query || '',
      url: `https://www.zhihu.com/search?type=content&q=${encodeURIComponent(item.query || '')}`,
    }));
  } catch (error) {
    console.error('备用获取知乎热榜失败:', error);
  }
  return [];
}

async function fetchToutiaoHotFallback(): Promise<NewsItem[]> {
  try {
    const response = await fetch('https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc', {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
      },
      cache: 'no-store',
    });
    const data = await response.json();
    const list = data?.data || [];
    return list.slice(0, 30).map((item: any) => ({
      title: item.Title || '',
      url: item.Url || `https://www.toutiao.com/trending/${item.ClusterIdStr || ''}/`,
      hot_score: item.HotValue ? String(item.HotValue) : '',
    }));
  } catch (error) {
    console.error('备用获取今日头条热榜失败:', error);
  }
  return [];
}

async function fetchThePaperHotFallback(): Promise<NewsItem[]> {
  try {
    const response = await fetch('https://cache.thepaper.cn/contentapi/wwwIndex/rightSidebar', {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': 'https://www.thepaper.cn/',
      },
      cache: 'no-store',
    });
    const data = await response.json();
    const hotNews = data?.data?.hotNews || [];
    return hotNews.slice(0, 30).map((item: any) => ({
      title: item.name || '',
      url: `https://www.thepaper.cn/newsDetail_forward_${item.contId}`,
      image: item.pic || item.smallPic || '',
      hot: item.praiseTimes ? `👍 ${item.praiseTimes}` : '',
    }));
  } catch (error) {
    console.error('备用获取澎湃新闻失败:', error);
  }
  return [];
}

async function fetch36KrHotFallback(): Promise<NewsItem[]> {
  try {
    const response = await fetch('https://36kr.com/newsflashes', {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
      },
      cache: 'no-store',
    });
    const html = await response.text();
    const pattern = /newsflashes\/(\d+)"[^>]*>([^<]+)<\/a>/g;
    const matches = [...html.matchAll(pattern)];
    const result: NewsItem[] = [];
    const seen = new Set<string>();

    for (const match of matches) {
      const itemId = match[1];
      const title = match[2].trim();
      if (title && title.length > 5 && !seen.has(title)) {
        seen.add(title);
        result.push({
          title,
          url: `https://36kr.com/newsflashes/${itemId}`,
        });
      }
    }
    return result.slice(0, 30);
  } catch (error) {
    console.error('备用获取36氪快讯失败:', error);
  }
  return [];
}

// 新闻源（这些源不使用 TrendRadar）
async function fetchThePaperTech(): Promise<NewsItem[]> {
  try {
    const response = await fetch('https://api.thepaper.cn/contentapi/nodeCont/getByChannelId', {
      method: 'POST',
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Content-Type': 'application/json',
        'Referer': 'https://www.thepaper.cn/',
      },
      cache: 'no-store',
      body: JSON.stringify({
        channelId: '119908',
        excludeContIds: [],
        listRecommendIds: [],
        province: null,
        pageSize: 20,
        startTime: null,
        pageNum: 1
      })
    });
    if (!response.ok) {
      throw new UpstreamNewsFetchError('ThePaper Tech upstream request failed', response.status);
    }
    const data = await response.json();
    const articles = data?.data?.list || [];
    return articles.map((item: any) => ({
      title: item.name || '',
      desc: item.summary || '',
      url: `https://www.thepaper.cn/newsDetail_forward_${item.contId}`,
      hot: item.praiseTimes ? `👍 ${item.praiseTimes}` : '',
      image: item.pic || item.smallPic || '',
    }));
  } catch (error) {
    console.error('获取澎湃科技失败:', error);
    if (error instanceof UpstreamNewsFetchError) {
      throw error;
    }
    throw new UpstreamNewsFetchError('ThePaper Tech upstream request failed');
  }
}

async function fetchOpenSource(): Promise<NewsItem[]> {
  try {
    const response = await fetch('https://api.github.com/search/repositories?q=stars:>1000&sort=stars&order=desc&per_page=30', {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
      },
      cache: 'no-store',
    });
    if (!response.ok) {
      throw new UpstreamNewsFetchError('Open source upstream request failed', response.status);
    }
    const data = await response.json();
    return (data?.items || []).map((item: any) => ({
      title: item.full_name || '',
      desc: item.description || '',
      url: item.html_url || '',
      hot: `⭐ ${item.stargazers_count || 0}`,
    }));
  } catch (error) {
    console.error('获取开源项目失败:', error);
    if (error instanceof UpstreamNewsFetchError) {
      throw error;
    }
    throw new UpstreamNewsFetchError('Open source upstream request failed');
  }
}

async function fetchRealtime(): Promise<NewsItem[]> {
  try {
    const response = await fetch('https://app.chinaz.com/djflkdsoisknfoklsyhownfrlewfknoiaewf/ai/GetAiInfoList.aspx?flag=zh_cn&type=1&page=1&pagesize=20', {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': 'https://app.chinaz.com/',
      },
      cache: 'no-store',
    });
    if (!response.ok) {
      throw new UpstreamNewsFetchError('Realtime upstream request failed', response.status);
    }
    const data = await response.json();
    const newsList = Array.isArray(data) ? data : (data?.data || []);
    return newsList.map((item: any) => ({
      title: item.Title || item.title || '',
      desc: item.Desc || item.desc || '',
      url: item.Url || item.url || '',
    }));
  } catch (error) {
    console.error('获取实时新闻失败:', error);
    if (error instanceof UpstreamNewsFetchError) {
      throw error;
    }
    throw new UpstreamNewsFetchError('Realtime upstream request failed');
  }
}

async function fetchSinaLive(): Promise<NewsItem[]> {
  try {
    const response = await fetch('https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2509&k=&num=50&page=1', {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': 'https://news.sina.com.cn/',
      },
      cache: 'no-store',
    });
    if (!response.ok) {
      throw new UpstreamNewsFetchError('Sina Live upstream request failed', response.status);
    }
    const data = await response.json();
    const newsList = data?.result?.data || [];
    return newsList.map((item: any) => ({
      title: item.title || '',
      url: item.url || '',
      desc: item.intro || '',
    }));
  } catch (error) {
    console.error('获取新浪直播失败:', error);
    if (error instanceof UpstreamNewsFetchError) {
      throw error;
    }
    throw new UpstreamNewsFetchError('Sina Live upstream request failed');
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: { source: string } }
) {
  const source = params.source;

  // 检查缓存
  const cached = cache.get(source);
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    return NextResponse.json({ items: cached.data, cached: true });
  }

  let items: NewsItem[] = [];

  try {
    // TrendRadar 支持的源 - 优先使用后端 API
    if (TRENDRADAR_SOURCES.includes(source)) {
      items = await fetchFromTrendRadar(source);

      // 如果 TrendRadar 返回空，尝试备用方案
      if (items.length === 0) {
        console.log(`TrendRadar 返回空，使用备用方案获取 ${source}`);
        switch (source) {
          case 'baidu':
            items = await fetchBaiduHotFallback();
            break;
          case 'weibo':
            items = await fetchWeiboHotFallback();
            break;
          case 'douyin':
            items = await fetchDouyinHotFallback();
            break;
          case 'bilibili':
            items = await fetchBilibiliHotFallback();
            break;
          case 'zhihu':
            items = await fetchZhihuHotFallback();
            break;
          case 'toutiao':
            items = await fetchToutiaoHotFallback();
            break;
          case 'thepaper':
            items = await fetchThePaperHotFallback();
            break;
          case '36kr':
            items = await fetch36KrHotFallback();
            break;
        }
      }
    } else {
      // 非 TrendRadar 源 - 直接爬取
      switch (source) {
        case 'thepaper-tech':
          items = await fetchThePaperTech();
          break;
        case 'opensource':
          items = await fetchOpenSource();
          break;
        case 'realtime':
          items = await fetchRealtime();
          break;
        case 'sina-live':
          items = await fetchSinaLive();
          break;
        case '36kr':
          items = await fetch36KrHotFallback();
          break;
        default:
          return NextResponse.json({ error: 'Invalid source' }, { status: 400 });
      }
    }

    // 更新缓存
    cache.set(source, { data: items, timestamp: Date.now() });

    return NextResponse.json({ items, cached: false });
  } catch (error) {
    console.error(`获取${source}数据失败:`, error);
    const status = error instanceof UpstreamNewsFetchError ? 502 : 500;
    return NextResponse.json({ error: 'Failed to fetch news' }, { status });
  }
}
