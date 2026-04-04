#!/usr/bin/env node

/**
 * TikHub API 共享客户端（小红书数据源）
 *
 * API Key 来源优先级：
 * 1. 脚本参数 --api-key
 * 2. ~/.alpha_insights.json 的 tikHubApiKey
 * 3. 环境变量 TIKHUB_API_KEY
 * 4. 内置默认 Key（部门公共账号）
 *
 * 网络：优先使用 Node.js fetch，若失败（企业代理/DNS 问题）自动降级为 curl
 */

const fs = require('fs');
const path = require('path');
const os = require('os');
const { execFileSync } = require('child_process');

const BASE_URL = 'https://api.tikhub.io';

// 保守请求间隔：1s
const DEFAULT_REQUEST_INTERVAL_MS = 1000;

/**
 * 加载配置
 */
function loadConfig() {
  try {
    const configPath = path.join(os.homedir(), '.alpha_insights.json');
    if (fs.existsSync(configPath)) {
      return JSON.parse(fs.readFileSync(configPath, 'utf8'));
    }
  } catch (error) {
    // 忽略
  }
  return null;
}

const config = loadConfig();

// 部门公共 API Key（TikHub），用户无需单独申请
const DEFAULT_API_KEY = null;

/**
 * 获取 API Key
 * 优先级：CLI 参数 > 配置文件 > 环境变量 > 内置默认
 */
function getApiKey(cliApiKey) {
  if (cliApiKey) return cliApiKey;
  if (config && config.tikHubApiKey) return config.tikHubApiKey;
  return process.env.TIKHUB_API_KEY || DEFAULT_API_KEY;
}

/**
 * 获取监控关键词列表（默认列表）
 */
function getMonitorKeywords() {
  if (config && config.xhsMonitorKeywords) {
    return config.xhsMonitorKeywords.split(',').map(s => s.trim()).filter(Boolean);
  }
  return [];
}

/**
 * 获取监控用户 ID 列表
 */
function getMonitorUserIds() {
  if (config && config.xhsMonitorUserIds) {
    return config.xhsMonitorUserIds.split(',').map(s => s.trim()).filter(Boolean);
  }
  return [];
}

/**
 * 延时
 */
function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

/**
 * 通过 curl 发送 HTTP 请求（用于企业代理环境）
 */
function curlRequest(url, options = {}) {
  const args = ['-s', '--connect-timeout', '15', '--max-time', '30'];
  args.push('-H', `Authorization: Bearer ${options.apiKey}`);

  if (options.method === 'POST') {
    args.push('-X', 'POST');
    args.push('-H', 'Content-Type: application/json');
    if (options.body) args.push('-d', JSON.stringify(options.body));
  }

  args.push(url);

  const result = execFileSync('curl', args, { encoding: 'utf8', timeout: 35000 });
  return JSON.parse(result);
}

/**
 * 调用 TikHub API（GET 请求）
 */
async function callTikHubAPI(endpoint, params = {}, apiKey) {
  const key = getApiKey(apiKey);
  if (!key) {
    throw new Error(
      'No TikHub API key found. 请先注册 https://tikhub.io 获取 API Token，' +
      '然后配置到 ~/.alpha_insights.json 的 tikHubApiKey 字段'
    );
  }

  const qs = new URLSearchParams(params).toString();
  const url = `${BASE_URL}${endpoint}${qs ? '?' + qs : ''}`;

  let data;
  try {
    const response = await fetch(url, {
      headers: { Authorization: `Bearer ${key}` },
      signal: AbortSignal.timeout(15000),
    });
    data = await response.json();
    if (!response.ok) {
      throw new Error(`TikHub API ${response.status}: ${data.detail?.message || data.message || JSON.stringify(data)}`);
    }
  } catch (e) {
    // fetch 失败（DNS/代理/网络问题），降级为 curl
    if (e instanceof TypeError || e.cause?.code) {
      data = curlRequest(url, { apiKey: key });
      if (data.detail?.code && data.detail.code >= 400) {
        throw new Error(`TikHub API ${data.detail.code}: ${data.detail.message || JSON.stringify(data.detail)}`);
      }
    } else {
      throw e;
    }
  }

  return data;
}

/**
 * 调用 TikHub API（POST 请求）
 */
async function callTikHubAPIPost(endpoint, body = {}, apiKey) {
  const key = getApiKey(apiKey);
  if (!key) {
    throw new Error(
      'No TikHub API key found. 请先注册 https://tikhub.io 获取 API Token，' +
      '然后配置到 ~/.alpha_insights.json 的 tikHubApiKey 字段'
    );
  }

  const url = `${BASE_URL}${endpoint}`;

  let data;
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${key}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(15000),
    });
    data = await response.json();
    if (!response.ok) {
      throw new Error(`TikHub API ${response.status}: ${data.detail?.message || data.message || JSON.stringify(data)}`);
    }
  } catch (e) {
    if (e instanceof TypeError || e.cause?.code) {
      data = curlRequest(url, { apiKey: key, method: 'POST', body });
      if (data.detail?.code && data.detail.code >= 400) {
        throw new Error(`TikHub API ${data.detail.code}: ${data.detail.message || JSON.stringify(data.detail)}`);
      }
    } else {
      throw e;
    }
  }

  return data;
}

/**
 * 批量调用，自动处理限流
 */
async function callTikHubAPIBatch(calls, apiKey) {
  const results = [];
  for (let i = 0; i < calls.length; i++) {
    const { endpoint, params, label } = calls[i];
    try {
      const data = await callTikHubAPI(endpoint, params, apiKey);
      results.push({ label, success: true, data });
    } catch (e) {
      results.push({ label, success: false, error: e.message });
    }
    if (i < calls.length - 1) {
      await sleep(DEFAULT_REQUEST_INTERVAL_MS);
    }
  }
  return results;
}

module.exports = {
  callTikHubAPI,
  callTikHubAPIPost,
  callTikHubAPIBatch,
  getApiKey,
  getMonitorKeywords,
  getMonitorUserIds,
  sleep,
  BASE_URL,
  DEFAULT_REQUEST_INTERVAL_MS,
};
