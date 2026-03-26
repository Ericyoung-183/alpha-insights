#!/usr/bin/env node

/**
 * 获取指定用户的最新小红书笔记
 */

const { parseArgs } = require('node:util');
const { callTikHubAPI, sleep, DEFAULT_REQUEST_INTERVAL_MS } = require('./tikhub_client');
const { normalizeNote } = require('./search_notes');

const USER_NOTES_ENDPOINTS = [
  '/api/v1/xiaohongshu/app/get_user_notes',
  '/api/v1/xiaohongshu/app_v2/get_user_posted_notes',
  '/api/v1/xiaohongshu/web/get_user_notes_v2',
];

async function fetchUserNotes(userId, count, apiKey) {
  let lastError;
  for (const endpoint of USER_NOTES_ENDPOINTS) {
    try {
      const data = await callTikHubAPI(endpoint, { user_id: userId }, apiKey);
      if (data.detail?.code && data.detail.code >= 400) continue;
      // 响应结构：data.data.notes (app) 或 data.data.data.notes 或 data.data.items (app_v2)
      const inner = data.data?.data || data.data || {};
      const items = inner.notes || inner.items || data.data?.notes || data.data?.items || [];
      return items.slice(0, count).map(item => {
        const note = normalizeNote(item);
        if (!note.authorId) note.authorId = userId;
        return note;
      });
    } catch (e) {
      lastError = e;
    }
  }
  throw lastError || new Error('All user notes endpoints failed');
}

async function main() {
  const options = {
    'user-id': { type: 'string' },
    count: { type: 'string' },
    'api-key': { type: 'string' },
    help: { type: 'boolean', short: 'h' },
  };

  try {
    const { values } = parseArgs({ options, allowPositionals: true });

    if (values.help) {
      console.log(`
Usage: fetch_user_notes.js --user-id <id> [options]

Options:
  --user-id <id>    小红书用户 ID，支持逗号分隔多用户 (必需)
  --count <n>       每个用户返回条数 (默认 5)
  --api-key <key>   TikHub API Key (可选)
  -h, --help        显示帮助

Examples:
  node fetch_user_notes.js --user-id "5a1234567890abcdef" --count 10
  node fetch_user_notes.js --user-id "uid1,uid2,uid3" --count 3
      `);
      return 0;
    }

    if (!values['user-id']) {
      console.error(JSON.stringify({ success: false, error: '--user-id is required' }));
      return 1;
    }

    const count = parseInt(values.count || '5', 10);
    const userIds = values['user-id'].split(',').map(s => s.trim()).filter(Boolean);

    if (userIds.length === 1) {
      const notes = await fetchUserNotes(userIds[0], count, values['api-key']);
      console.log(JSON.stringify({
        success: true,
        data: { userId: userIds[0], notes },
      }, null, 2));
    } else {
      const results = [];
      for (let i = 0; i < userIds.length; i++) {
        try {
          const notes = await fetchUserNotes(userIds[i], count, values['api-key']);
          results.push({ userId: userIds[i], notes });
        } catch (e) {
          results.push({ userId: userIds[i], error: e.message, notes: [] });
        }
        if (i < userIds.length - 1) {
          await sleep(DEFAULT_REQUEST_INTERVAL_MS);
        }
      }
      console.log(JSON.stringify({ success: true, data: { users: results } }, null, 2));
    }
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

module.exports = { fetchUserNotes };
