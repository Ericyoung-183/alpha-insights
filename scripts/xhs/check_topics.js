#!/usr/bin/env node

/**
 * 批量扫描小红书关键词/用户动态
 *
 * 两种扫描模式：
 * 1. 关键词模式（默认）：搜索预设关键词，按时间过滤
 * 2. 用户模式：获取指定用户最新笔记
 *
 * 适用于定时任务（cron）自动执行。
 */

const { parseArgs } = require('node:util');
const {
  getMonitorKeywords,
  getMonitorUserIds,
  sleep,
  DEFAULT_REQUEST_INTERVAL_MS,
} = require('./tikhub_client');
const { searchNotes } = require('./search_notes');
const { fetchUserNotes } = require('./fetch_user_notes');

/**
 * 解析 --since 参数为毫秒时间戳
 */
function parseSince(sinceStr) {
  if (!sinceStr) return Date.now() - 24 * 60 * 60 * 1000; // 默认 24h
  const match = sinceStr.match(/^(\d+)(h|d|m)$/);
  if (!match) return Date.now() - 24 * 60 * 60 * 1000;
  const num = parseInt(match[1], 10);
  const unit = match[2];
  const ms = unit === 'h' ? num * 3600000 : unit === 'd' ? num * 86400000 : num * 60000;
  return Date.now() - ms;
}

/**
 * 通过关键词搜索笔记（复用 searchNotes 的端点 fallback）
 */
async function scanByKeywords(keywords, sinceTs, apiKey) {
  const notes = [];
  const errors = [];
  const seenIds = new Set();

  for (let i = 0; i < keywords.length; i++) {
    const keyword = keywords[i];
    try {
      const results = await searchNotes(keyword, 'time_descending', apiKey);
      for (const note of results) {
        if (seenIds.has(note.noteId)) continue;
        seenIds.add(note.noteId);
        if (note.createTime) {
          const noteTs = new Date(note.createTime).getTime();
          if (noteTs < sinceTs) continue;
        }
        note.matchedKeyword = keyword;
        notes.push(note);
      }
    } catch (e) {
      errors.push({ keyword, error: e.message });
    }

    if (i < keywords.length - 1) {
      await sleep(DEFAULT_REQUEST_INTERVAL_MS);
    }
  }

  return { notes, errors };
}

/**
 * 通过用户 ID 获取笔记（复用 fetchUserNotes 的端点 fallback）
 */
async function scanByUsers(userIds, sinceTs, apiKey) {
  const notes = [];
  const errors = [];
  const seenIds = new Set();

  for (let i = 0; i < userIds.length; i++) {
    const userId = userIds[i];
    try {
      const results = await fetchUserNotes(userId, 20, apiKey);
      for (const note of results) {
        if (seenIds.has(note.noteId)) continue;
        seenIds.add(note.noteId);
        if (note.createTime) {
          const noteTs = new Date(note.createTime).getTime();
          if (noteTs < sinceTs) continue;
        }
        note.source = 'user_monitor';
        notes.push(note);
      }
    } catch (e) {
      errors.push({ userId, error: e.message });
    }

    if (i < userIds.length - 1) {
      await sleep(DEFAULT_REQUEST_INTERVAL_MS);
    }
  }

  return { notes, errors };
}

async function checkTopics(keywords, userIds, sinceStr, apiKey) {
  const sinceTs = parseSince(sinceStr);
  const sinceDate = new Date(sinceTs).toISOString();

  let allNotes = [];
  const errors = [];

  // 关键词扫描
  if (keywords.length > 0) {
    const result = await scanByKeywords(keywords, sinceTs, apiKey);
    allNotes.push(...result.notes);
    errors.push(...result.errors);
  }

  // 用户扫描
  if (userIds.length > 0) {
    const result = await scanByUsers(userIds, sinceTs, apiKey);
    // 去重（可能与关键词结果重复）
    const seenIds = new Set(allNotes.map(n => n.noteId));
    for (const note of result.notes) {
      if (!seenIds.has(note.noteId)) {
        allNotes.push(note);
      }
    }
    errors.push(...result.errors);
  }

  // 按互动量排序（点赞 + 收藏 + 评论）
  allNotes.sort((a, b) => {
    const scoreA = (a.likeCount || 0) + (a.collectCount || 0) + (a.commentCount || 0);
    const scoreB = (b.likeCount || 0) + (b.collectCount || 0) + (b.commentCount || 0);
    return scoreB - scoreA;
  });

  return {
    summary: {
      keywordsScanned: keywords.length,
      usersScanned: userIds.length,
      sinceTime: sinceDate,
      totalNotes: allNotes.length,
      errors: errors.length,
    },
    notes: allNotes,
    errors,
  };
}

async function main() {
  const options = {
    keywords: { type: 'string' },
    'user-ids': { type: 'string' },
    since: { type: 'string' },
    'api-key': { type: 'string' },
    help: { type: 'boolean', short: 'h' },
  };

  try {
    const { values } = parseArgs({ options, allowPositionals: true });

    if (values.help) {
      console.log(`
Usage: check_topics.js [options]

Options:
  --keywords <list>     逗号分隔的关键词列表 (默认使用配置文件中的 xhsMonitorKeywords)
  --user-ids <list>     逗号分隔的用户 ID 列表 (默认使用配置文件中的 xhsMonitorUserIds)
  --since <duration>    时间范围: 1h/6h/24h/7d (默认 24h)
  --api-key <key>       TikHub API Key (可选)
  -h, --help            显示帮助

Examples:
  node check_topics.js --keywords "AI编程,Cursor" --since 24h
  node check_topics.js --user-ids "uid1,uid2" --since 6h
  node check_topics.js --keywords "WeaveFox" --user-ids "uid1" --since 12h
      `);
      return 0;
    }

    const keywords = values.keywords
      ? values.keywords.split(',').map(s => s.trim()).filter(Boolean)
      : getMonitorKeywords();

    const userIds = values['user-ids']
      ? values['user-ids'].split(',').map(s => s.trim()).filter(Boolean)
      : getMonitorUserIds();

    if (keywords.length === 0 && userIds.length === 0) {
      console.error(JSON.stringify({
        success: false,
        error: '请指定 --keywords 或 --user-ids，或在 ~/.alpha_insights.json 中配置 xhsMonitorKeywords / xhsMonitorUserIds',
      }));
      return 1;
    }

    const result = await checkTopics(keywords, userIds, values.since, values['api-key']);
    console.log(JSON.stringify({ success: true, data: result }, null, 2));
    return 0;
  } catch (e) {
    console.error(JSON.stringify({ success: false, error: e.message }, null, 2));
    return 1;
  }
}

if (require.main === module) {
  main()
    .then(exitCode => { process.exitCode = exitCode; })
    .catch(err => { console.error(err); process.exitCode = 1; });
}
