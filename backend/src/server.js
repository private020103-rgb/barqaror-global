const http = require('http');
const { URL } = require('url');

const PORT = process.env.PORT || 3000;

const FEEDS = [
  { name: 'OpenAI News', url: 'https://openai.com/news/rss.xml', category: 'AI' },
  { name: 'Google AI Blog', url: 'https://blog.google/technology/ai/rss/', category: 'AI' },
  { name: 'MIT News - AI', url: 'https://news.mit.edu/rss/topic/artificial-intelligence2', category: 'AI' },
  { name: 'AI News', url: 'https://www.artificialintelligence-news.com/feed/', category: 'AI' }
];

function decodeXmlEntities(text) {
  return text
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, '$1')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'");
}

function stripHtml(text) {
  return text
    .replace(/<[^>]*>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function extractTagValue(xmlChunk, tagNames) {
  for (const tag of tagNames) {
    const regex = new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`, 'i');
    const match = xmlChunk.match(regex);
    if (match && match[1]) {
      return decodeXmlEntities(match[1]).trim();
    }
  }
  return '';
}

function parseRssItems(xml) {
  const itemBlocks = [...xml.matchAll(/<item[\s\S]*?<\/item>/gi)].map((m) => m[0]);
  if (itemBlocks.length > 0) {
    return itemBlocks.map((item) => ({
      title: extractTagValue(item, ['title']),
      link: extractTagValue(item, ['link', 'guid']),
      summary: extractTagValue(item, ['description', 'content:encoded']),
      publishedAt: extractTagValue(item, ['pubDate', 'dc:date'])
    }));
  }

  const entryBlocks = [...xml.matchAll(/<entry[\s\S]*?<\/entry>/gi)].map((m) => m[0]);
  return entryBlocks.map((entry) => {
    const atomLinkMatch = entry.match(/<link[^>]*href=["']([^"']+)["'][^>]*>/i);

    return {
      title: extractTagValue(entry, ['title']),
      link: atomLinkMatch ? atomLinkMatch[1] : extractTagValue(entry, ['id']),
      summary: extractTagValue(entry, ['summary', 'content']),
      publishedAt: extractTagValue(entry, ['updated', 'published'])
    };
  });
}

function normalizeItem(item, feed) {
  const publishedAt = new Date(item.publishedAt || Date.now()).toISOString();
  return {
    title: item.title || 'Untitled',
    summary: stripHtml(item.summary || '').slice(0, 320),
    sourceName: feed.name,
    sourceUrl: item.link || '',
    publishedAt,
    category: feed.category
  };
}

function dedupeNews(items) {
  const urlSet = new Set();
  const titleTimeSet = new Set();

  return items.filter((item) => {
    const urlKey = (item.sourceUrl || '').trim();
    const titleTimeKey = `${item.title.toLowerCase().trim()}|${item.publishedAt}`;

    if (urlKey && urlSet.has(urlKey)) return false;
    if (titleTimeSet.has(titleTimeKey)) return false;

    if (urlKey) urlSet.add(urlKey);
    titleTimeSet.add(titleTimeKey);
    return true;
  });
}

async function fetchFeed(feed) {
  const response = await fetch(feed.url, {
    headers: { 'User-Agent': 'barqaror-global-bot/1.0' }
  });

  if (!response.ok) {
    throw new Error(`Feed status ${response.status}`);
  }

  const xml = await response.text();
  const parsedItems = parseRssItems(xml);
  return parsedItems.map((item) => normalizeItem(item, feed));
}

async function fetchAllFeeds() {
  const settled = await Promise.allSettled(FEEDS.map((feed) => fetchFeed(feed)));
  const items = [];
  const errors = [];

  settled.forEach((result, index) => {
    if (result.status === 'fulfilled') {
      items.push(...result.value);
    } else {
      errors.push({
        sourceName: FEEDS[index].name,
        message: result.reason?.message || 'Unknown feed error'
      });
    }
  });

  const unique = dedupeNews(items).sort(
    (a, b) => new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime()
  );

  return { items: unique, errors };
}

function sendJson(res, statusCode, data) {
  const body = JSON.stringify(data);
  res.writeHead(statusCode, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(body)
  });
  res.end(body);
}

const server = http.createServer(async (req, res) => {
  const requestUrl = new URL(req.url, `http://${req.headers.host}`);

  if (req.method === 'GET' && requestUrl.pathname === '/health') {
    return sendJson(res, 200, { status: 'ok' });
  }

  if (req.method === 'GET' && requestUrl.pathname === '/api/news') {
    try {
      const { items, errors } = await fetchAllFeeds();

      if (items.length === 0) {
        return sendJson(res, 200, {
          items: [],
          message: 'Fallback: hozircha yangiliklar mavjud emas.',
          errors
        });
      }

      return sendJson(res, 200, {
        items,
        message: errors.length
          ? "Qisman muvaffaqiyat: ba'zi manbalardan ma'lumot olinmadi."
          : 'Muvaffaqiyatli',
        errors
      });
    } catch (error) {
      return sendJson(res, 200, {
        items: [],
        message: 'Fallback: yangiliklarni olishda xatolik yuz berdi.',
        error: error.message
      });
    }
  }

  return sendJson(res, 404, { message: 'Not Found' });
});

server.listen(PORT, () => {
  console.log(`Backend service is running on port ${PORT}`);
});
