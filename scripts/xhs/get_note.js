#!/usr/bin/env node

/**
 * 获取小红书笔记详情
 * 支持通过 note_id 或分享链接获取
 */

const { parseArgs } = require('node:util');
const { callTikHubAPI } = require('./tikhub_client');

/**
 * 从分享链接中提取 note_id
 * 支持格式：
 * - https://www.xiaohongshu.com/explore/66c9cc31000000001f03a4bc
 * - https://www.xiaohongshu.com/discovery/item/66c9cc31000000001f03a4bc
 * - https://xhslink.com/xxx（短链接，需要通过 API 解析）
 */
function extractNoteId(url) {
  const match = url.match(/xiaohongshu\.com\/(?:explore|discovery\/item)\/([a-f0-9]{24})/);
  if (match) return { noteId: match[1], needResolve: false };

  if (url.includes('xhslink.com') || url.includes('xiaohongshu.com')) {
    return { noteId: null, needResolve: true, url };
  }

  return { noteId: null, needResolve: false };
}

/**
 * 通过分享链接解析 note_id
 */
const RESOLVE_ENDPOINTS = [
  { endpoint: '/api/v1/xiaohongshu/web/get_note_id_and_xsec_token', paramKey: 'share_text' },
  { endpoint: '/api/v1/xiaohongshu/app/extract_share_info', paramKey: 'share_text' },
];

async function resolveNoteId(shareUrl, apiKey) {
  for (const { endpoint, paramKey } of RESOLVE_ENDPOINTS) {
    try {
      const data = await callTikHubAPI(endpoint, { [paramKey]: shareUrl }, apiKey);
      if (data.detail?.code && data.detail.code >= 400) continue;
      const noteId = data.data?.note_id || data.note_id || null;
      if (noteId) return noteId;
    } catch (e) {
      // try next
    }
  }
  return null;
}

const NOTE_DETAIL_ENDPOINTS = [
  '/api/v1/xiaohongshu/app/get_note_info',
  '/api/v1/xiaohongshu/app_v2/get_mixed_note_detail',
  '/api/v1/xiaohongshu/web/get_note_info_v7',
];

async function getNoteDetail(noteId, apiKey) {
  let data;
  let lastError;
  for (const endpoint of NOTE_DETAIL_ENDPOINTS) {
    try {
      data = await callTikHubAPI(endpoint, { note_id: noteId }, apiKey);
      if (data.detail?.code && data.detail.code >= 400) { data = null; continue; }
      break;
    } catch (e) {
      lastError = e;
      data = null;
    }
  }
  if (!data) throw lastError || new Error('All note detail endpoints failed');

  // 兼容多种响应结构：
  // app/get_note_info:          data.data[0].note_list[0]  (data.data 是数组)
  // app_v2/get_mixed_note_detail: data.data.note_list[0]   (data.data 是对象)
  // web/get_note_info_v7:       data.data.items[0].note_card
  const inner = data.data?.data || data.data;
  let noteData = {};
  let topUser = {};

  if (Array.isArray(inner) && inner[0]) {
    // app/get_note_info: data.data 是数组，每项有 user + note_list
    topUser = inner[0].user || {};
    noteData = inner[0].note_list?.[0] || inner[0];
  } else if (inner?.note_list) {
    // app_v2 格式
    topUser = inner.user || {};
    noteData = inner.note_list[0] || inner;
  } else if (inner?.items) {
    // web 格式: items[0].note_card
    noteData = inner.items[0]?.note_card || inner.items[0] || {};
    topUser = noteData.user || {};
  } else {
    noteData = inner || {};
    topUser = noteData.user || {};
  }

  const user = noteData.user || topUser;
  const interact = noteData.interact_info || {};
  const ts = noteData.timestamp || noteData.time || noteData.last_update_time || 0;

  return {
    noteId,
    title: noteData.display_title || noteData.title || '',
    content: noteData.desc || '',
    type: noteData.type === 'video' ? 'video' : 'image',
    likeCount: parseInt(noteData.liked_count ?? interact.liked_count ?? 0) || 0,
    collectCount: parseInt(noteData.collected_count ?? interact.collected_count ?? 0) || 0,
    commentCount: parseInt(noteData.comments_count ?? interact.comment_count ?? 0) || 0,
    shareCount: parseInt(noteData.shared_count ?? interact.share_count ?? 0) || 0,
    author: user.nickname || user.name || '',
    authorId: user.user_id || user.userid || user.id || '',
    createTime: ts ? new Date(ts * 1000).toISOString() : '',
    tags: (noteData.tag_list || noteData.topics || []).map(t => t.name).filter(Boolean),
    imageCount: (noteData.image_list || noteData.images_list || []).length,
    url: `https://www.xiaohongshu.com/explore/${noteId}`,
  };
}

async function main() {
  const options = {
    'note-id': { type: 'string' },
    url: { type: 'string' },
    'api-key': { type: 'string' },
    help: { type: 'boolean', short: 'h' },
  };

  try {
    const { values } = parseArgs({ options, allowPositionals: true });

    if (values.help) {
      console.log(`
Usage: get_note.js --note-id <id> | --url <share_url> [options]

Options:
  --note-id <id>     笔记 ID (与 --url 二选一)
  --url <url>        笔记分享链接 (与 --note-id 二选一，自动解析 note_id)
  --api-key <key>    TikHub API Key (可选)
  -h, --help         显示帮助

Examples:
  node get_note.js --note-id "66c9cc31000000001f03a4bc"
  node get_note.js --url "https://www.xiaohongshu.com/explore/66c9cc31000000001f03a4bc"
  node get_note.js --url "https://xhslink.com/xxx"
      `);
      return 0;
    }

    let noteId = values['note-id'];

    if (!noteId && values.url) {
      const parsed = extractNoteId(values.url);
      if (parsed.noteId) {
        noteId = parsed.noteId;
      } else if (parsed.needResolve) {
        noteId = await resolveNoteId(values.url, values['api-key']);
        if (!noteId) {
          console.error(JSON.stringify({ success: false, error: 'Failed to resolve note_id from URL' }));
          return 1;
        }
      }
    }

    if (!noteId) {
      console.error(JSON.stringify({ success: false, error: '--note-id or --url is required' }));
      return 1;
    }

    const note = await getNoteDetail(noteId, values['api-key']);
    console.log(JSON.stringify({ success: true, data: note }, null, 2));
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

module.exports = { getNoteDetail, resolveNoteId, extractNoteId };
