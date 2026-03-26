#!/usr/bin/env node
/**
 * 小红书笔记搜索（支持多页）
 * 通过关键词搜索小红书笔记，支持排序方式选择、多页搜索
 */

const { parseArgs } = require('node:util');
const { callTikHubAPI } = require('./tikhub_client');

/**
 * 标准化笔记数据
 *
 * 兼容多种 API 响应格式：
 * - app_v2/search_notes: { model_type, note: { id, title, liked_count, ... } }
 * - app/get_note_info:   data.data[0].note_list[0] → { id, title, liked_count, ... }
 * - app/get_user_notes:  data.data.notes[i] → { note_card: {...}, ... } 或扁平结构
 */
function normalizeNote(item) {
  // 搜索结果: item.note 包装；笔记详情/用户笔记: item.note_card 或直接扁平
  const note = item.note || item.note_card || item;
  const user = note.user || {};
  const noteId = note.note_id || note.id || item.id || '';

  // 互动数据：优先扁平字段（app_v2），fallback interact_info（旧格式）
  const interact = note.interact_info || {};
  const likeCount = parseInt(note.liked_count ?? interact.liked_count ?? 0) || 0;
  const collectCount = parseInt(note.collected_count ?? interact.collected_count ?? 0) || 0;
  const commentCount = parseInt(note.comments_count ?? interact.comment_count ?? 0) || 0;
  const shareCount = parseInt(note.shared_count ?? interact.share_count ?? 0) || 0;

  // 时间：优先 timestamp / time（秒级 unix），fallback last_update_time
  const ts = note.timestamp || note.time || note.last_update_time || 0;

  return {
    noteId,
    title: note.display_title || note.title || '',
    content: note.desc || '',
    type: note.type === 'video' ? 'video' : 'image',
    likeCount,
    collectCount,
    commentCount,
    shareCount,
    author: user.nickname || user.name || '',
    authorId: user.user_id || user.userid || user.id || '',
    createTime: ts ? new Date(ts * 1000).toISOString() : '',
    url: noteId ? `https://www.xiaohongshu.com/explore/${noteId}` : '',
  };
}

// 搜索端点优先级：app_v2 > app > web_v2
// 注意：部分"可选"参数实际必传，否则返回 400
const SEARCH_ENDPOINTS = [
  {
    endpoint: '/api/v1/xiaohongshu/app_v2/search_notes',
    buildParams: (kw, sort, page = 1) => ({
      keyword: kw, page: page,
      sort_type: sort || 'general',
      note_type: '不限', time_filter: '不限',
      source: 'explore_feed', ai_mode: 0,
    }),
  },
  {
    endpoint: '/api/v1/xiaohongshu/app/search_notes',
    buildParams: (kw, sort, page = 1) => ({
      keyword: kw, page: page,
      sort_type: sort || 'general',
      filter_note_type: '不限', filter_note_time: '不限',
    }),
  },
  {
    endpoint: '/api/v1/xiaohongshu/web_v2/fetch_search_notes',
    buildParams: (kw, sort, page = 1) => ({
      keywords: kw, page: page,
      sort_type: sort || 'general',
      note_type: '0',
    }),
  },
];

/**
 * 延迟函数（避免 API 速率限制）
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * 搜索单页笔记
 */
async function searchNotesPage(keyword, sort, page, apiKey) {
  let lastError;
  for (const { endpoint, buildParams } of SEARCH_ENDPOINTS) {
    try {
      const data = await callTikHubAPI(endpoint, buildParams(keyword, sort, page), apiKey);
      // 成功响应（code 200 或无 detail.code）
      if (data.detail?.code && data.detail.code >= 400) continue;
      // 响应结构：data.data.items (app_v2/app) 或 data.items (web_v2)
      const inner = data.data?.data?.items || data.data?.items || data.data?.notes || data.items || [];
      return inner
        .filter(item => item.model_type === 'note' || item.note_card || item.note || item.note_id || item.id)
        .map(normalizeNote);
    } catch (e) {
      lastError = e;
    }
  }
  throw lastError || new Error(`Search failed for page ${page}`);
}

/**
 * 多页搜索笔记（含去重）
 */
async function searchNotes(keyword, sort, maxPages = 1, apiKey) {
  const allNotes = [];
  const seenIds = new Set();

  for (let page = 1; page <= maxPages; page++) {
    try {
      const notes = await searchNotesPage(keyword, sort, page, apiKey);
      
      // 去重：只保留未出现的 noteId
      const newNotes = notes.filter(note => {
        if (seenIds.has(note.noteId)) {
          return false;
        }
        seenIds.add(note.noteId);
        return true;
      });

      allNotes.push(...newNotes);

      // 如果新页没有新笔记，说明已到底
      if (newNotes.length === 0) {
        console.error(`No new notes on page ${page}, stopping Pagination...`);
        break;
      }

      // 延迟 1000ms 避免 API 速率限制
      if (page < maxPages) {
        await sleep(1000);
      }
    } catch (e) {
      console.error(`Page ${page} search failed: ${e.message}`);
      // 单页失败不影响其他页
    }
  }

  return allNotes;
}

async function main() {
  const options = {
    keyword: { type: 'string' },
    sort: { type: 'string' },
    'max-pages': { type: 'string' },
    'api-key': { type: 'string' },
    help: { type: 'boolean', short: 'h' },
  };

  try {
    const { values } = parseArgs({ options, allowPositionals: true });

    if (values.help) {
      console.log(`
Usage: search_notes.js --keyword <text> [options]

Options:
  --keyword <text>      搜索关键词 (必需)
  --sort <type>         排序方式: general | time_descending | popularity_descending (默认 general)
  --max-pages <num>     最大翻页数 (默认 1, 推荐 15)
  --api-key <key>       TikHub API Key (可选)
  -h, --help            显示帮助

Examples:
  node search_notes.js --keyword "AI编程" --max-pages 5
  node search_notes.js --keyword "新能源汽车" --max-pages 15 --sort popularity_descending
      `);
      return 0;
    }

    if (!values.keyword) {
      console.error(JSON.stringify({ success: false, error: '--keyword is required' }));
      return 1;
    }

    const maxPages = values['max-pages'] ? parseInt(values['max-pages'], 10) : 1;
    if (isNaN(maxPages) || maxPages < 1) {
      console.error(JSON.stringify({ success: false, error: '--max-pages must be a positive number' }));
      return 1;
    }

    console.error(`Searching "${values.keyword}" with max ${maxPages} pages...`);

    const notes = await searchNotes(values.keyword, values.sort, maxPages, values['api-key']);

    console.error(`Found ${notes.length} unique notes across pages`);
    
    console.log(JSON.stringify({
      success: true,
      data: { 
        keyword: values.keyword, 
        maxPagesSearched: maxPages,
        count: notes.length, 
        notes 
      },
    }, null, 2));
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

module.exports = { searchNotes, searchNotesPage, normalizeNote };
