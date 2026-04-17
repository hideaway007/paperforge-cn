#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PROJECT_ROOT = path.resolve(__dirname, '..', '..');

const TASK_PATH = path.join(PROJECT_ROOT, 'outputs', 'part1', 'cnki_task.txt');
const MANIFEST_PATH = path.join(PROJECT_ROOT, 'outputs', 'part1', 'download_manifest.json');
const PAPERS_DIR = path.join(PROJECT_ROOT, 'raw-library', 'papers');
const PROVENANCE_DIR = path.join(PROJECT_ROOT, 'raw-library', 'provenance');
const TMP_DOWNLOAD_DIR = path.join(PAPERS_DIR, '.tmp-downloads');
const CNKI_HOME = 'https://www.cnki.net';
const CNKI_ADVANCED = 'https://kns.cnki.net/kns8s/AdvSearch';
function positiveIntFromEnv(name, fallback) {
  const raw = process.env[name];
  if (!raw) return fallback;
  const value = Number(raw);
  if (!Number.isInteger(value) || value <= 0) {
    throw new Error(`${name} must be a positive integer`);
  }
  return value;
}

const MAX_DOWNLOADS = positiveIntFromEnv('PART1_CNKI_MAX_DOWNLOADS', 28);
const PER_QUERY_SUCCESS_CAP = Math.min(positiveIntFromEnv('PART1_CNKI_PER_QUERY_CAP', 100), MAX_DOWNLOADS);

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const jitter = (minMs, maxMs) => delay(minMs + Math.floor(Math.random() * (maxMs - minMs + 1)));
const isoNow = () => new Date().toISOString();

function ensureDirs() {
  for (const dir of [PAPERS_DIR, PROVENANCE_DIR, path.dirname(MANIFEST_PATH)]) {
    fs.mkdirSync(dir, { recursive: true });
  }
  ensureSafeTmpDownloadDir();
}

function ensureSafeTmpDownloadDir() {
  const papersRealPath = fs.realpathSync(PAPERS_DIR);
  if (fs.existsSync(TMP_DOWNLOAD_DIR)) {
    const stat = fs.lstatSync(TMP_DOWNLOAD_DIR);
    if (stat.isSymbolicLink()) {
      throw new Error(`${TMP_DOWNLOAD_DIR} must not be a symlink`);
    }
    if (!stat.isDirectory()) {
      throw new Error(`${TMP_DOWNLOAD_DIR} must be a directory`);
    }
  } else {
    fs.mkdirSync(TMP_DOWNLOAD_DIR, { recursive: true });
  }
  const tmpRealPath = fs.realpathSync(TMP_DOWNLOAD_DIR);
  const relative = path.relative(papersRealPath, tmpRealPath);
  if (relative.startsWith('..') || path.isAbsolute(relative)) {
    throw new Error(`${TMP_DOWNLOAD_DIR} must stay inside ${PAPERS_DIR}`);
  }
}

function readChromeEndpoint() {
  if (process.env.CNKI_CDP_ENDPOINT) return process.env.CNKI_CDP_ENDPOINT;
  const candidates = [
    path.join(process.env.HOME, 'Library/Application Support/Google/Chrome/DevToolsActivePort'),
    path.join(process.env.HOME, 'Library/Application Support/Google/Chrome Canary/DevToolsActivePort'),
    path.join(process.env.HOME, 'Library/Application Support/Chromium/DevToolsActivePort'),
  ];
  for (const candidate of candidates) {
    if (!fs.existsSync(candidate)) continue;
    const [port, wsPath] = fs.readFileSync(candidate, 'utf8').trim().split(/\n/);
    if (port && wsPath) return `ws://127.0.0.1:${port}${wsPath}`;
  }
  throw new Error('Chrome DevToolsActivePort not found. Set CNKI_CDP_ENDPOINT or open Chrome remote debugging and rerun.');
}

function parseQueries(taskText) {
  return taskText
    .split(/\n\s*-\s+query_id:\s+/)
    .slice(1)
    .map((block) => {
      const queryId = block.match(/^(\S+)/)?.[1]?.trim();
      const termsText = block.match(/terms:\s*(.+)/)?.[1]?.trim() || '';
      const field = block.match(/field:\s*(.+)/)?.[1]?.trim() || '主题';
      const year = block.match(/year:\s*(\d{4})-(\d{4})/);
      const docType = block.match(/doc_type:\s*(.+)/)?.[1]?.trim() || '期刊论文';
      const quotedTerms = [...termsText.matchAll(/"([^"]+)"/g)].map((match) => match[1]);
      const terms = quotedTerms.length > 0 ? quotedTerms : [termsText.replace(/^"|"$/g, '')].filter(Boolean);
      const operator = /\sOR\s/i.test(termsText) ? 'OR' : 'AND';
      return {
        query_id: queryId,
        terms,
        field,
        operator,
        year_from: year ? Number(year[1]) : 2005,
        year_to: year ? Number(year[2]) : 2025,
        doc_type: docType,
      };
    })
    .filter((query) => query.query_id && query.terms.length > 0);
}

function cnkiExpression(query) {
  if (query.operator === 'OR') {
    return query.terms.map((term) => `"${term}"`).join(' + ');
  }
  return query.terms.map((term) => (query.terms.length === 1 ? term : `"${term}"`)).join(' * ');
}

function normalizeText(text) {
  return String(text || '').replace(/\s+/g, ' ').trim();
}

function titleKey(title, year) {
  return `${String(title || '').replace(/\s+/g, '').toLowerCase()}::${year || ''}`;
}

function parseResultTotal(text) {
  const match = String(text || '').match(/共找到\s*([\d,]+)\s*条结果/);
  return match ? Number(match[1].replace(/,/g, '')) : 0;
}

function nextCountersFromDisk() {
  const counters = new Map();
  if (!fs.existsSync(PROVENANCE_DIR)) return counters;
  for (const file of fs.readdirSync(PROVENANCE_DIR)) {
    const match = file.match(/^cnki_(\d{4})_(\d{3})\.json$/);
    if (!match) continue;
    const year = Number(match[1]);
    const seq = Number(match[2]);
    counters.set(year, Math.max(counters.get(year) || 0, seq));
  }
  return counters;
}

function nextSourceId(year, counters) {
  const normalizedYear = Number.isInteger(year) && year > 0 ? year : new Date().getFullYear();
  const next = (counters.get(normalizedYear) || 0) + 1;
  counters.set(normalizedYear, next);
  return `cnki_${normalizedYear}_${String(next).padStart(3, '0')}`;
}

function existingTitleKeys() {
  const keys = new Set();
  if (!fs.existsSync(PROVENANCE_DIR)) return keys;
  for (const file of fs.readdirSync(PROVENANCE_DIR)) {
    if (!/^cnki_.*\.json$/.test(file)) continue;
    try {
      const data = JSON.parse(fs.readFileSync(path.join(PROVENANCE_DIR, file), 'utf8'));
      keys.add(titleKey(data.title, data.year));
    } catch {
      // Ignore malformed pre-existing provenance instead of silently repairing it.
    }
  }
  return keys;
}

function cleanupTmpDownloads() {
  ensureSafeTmpDownloadDir();
  if (!fs.existsSync(TMP_DOWNLOAD_DIR)) return;
  for (const file of fs.readdirSync(TMP_DOWNLOAD_DIR)) {
    const target = path.join(TMP_DOWNLOAD_DIR, file);
    const targetStat = fs.lstatSync(target);
    if (targetStat.isSymbolicLink()) {
      fs.unlinkSync(target);
      continue;
    }
    fs.rmSync(target, { force: true, recursive: true });
  }
}

function isPdf(filePath) {
  if (!fs.existsSync(filePath)) return false;
  if (!fs.statSync(filePath).isFile()) return false;
  const fd = fs.openSync(filePath, 'r');
  try {
    const buffer = Buffer.alloc(5);
    fs.readSync(fd, buffer, 0, 5, 0);
    return buffer.toString('utf8') === '%PDF-';
  } finally {
    fs.closeSync(fd);
  }
}

function pathInside(childPath, parentPath) {
  const child = path.resolve(childPath);
  const parent = path.resolve(parentPath);
  const relative = path.relative(parent, child);
  return relative === '' || (relative && !relative.startsWith('..') && !path.isAbsolute(relative));
}

function assertSafeDownloadedPdfPath(downloadedPath) {
  const resolved = path.resolve(downloadedPath);
  if (!pathInside(resolved, TMP_DOWNLOAD_DIR)) {
    throw new Error(`unsafe Chrome download path outside temp download dir: ${resolved}`);
  }
  if (!fs.existsSync(resolved)) {
    throw new Error(`download event completed but file is missing: ${resolved}`);
  }
  if (!fs.statSync(resolved).isFile()) {
    throw new Error(`download path is not a file: ${resolved}`);
  }
  return resolved;
}

function assertSafeTargetPdfPath(targetPdf) {
  const resolved = path.resolve(targetPdf);
  if (!pathInside(resolved, PAPERS_DIR)) {
    throw new Error(`unsafe target PDF path outside papers dir: ${resolved}`);
  }
  return resolved;
}

function fatalCdpError(message) {
  const error = new Error(message);
  error.fatalCdp = true;
  return error;
}

function isFatalCdpError(error) {
  const message = String(error?.message || error || '');
  return Boolean(error?.fatalCdp) || [
    /Session with given id not found/i,
    /Target closed/i,
    /WebSocket not open/i,
    /Browser closed/i,
    /ECONNRESET/i,
    /socket hang up/i,
    /connection closed/i,
    /disconnected/i,
  ].some((pattern) => pattern.test(message));
}

class Cdp {
  constructor(wsUrl) {
    this.wsUrl = wsUrl;
    this.ws = null;
    this.connected = false;
    this.disconnectReason = null;
    this.nextId = 1;
    this.pending = new Map();
    this.downloads = new Map();
  }

  async connect() {
    this.ws = new WebSocket(this.wsUrl);
    this.ws.addEventListener('message', (event) => this.handleMessage(event));
    this.ws.addEventListener('close', () => this.markDisconnected('Browser closed CDP WebSocket'));
    this.ws.addEventListener('error', (event) => {
      const message = event?.error?.message || event?.message || 'CDP WebSocket error';
      this.markDisconnected(message);
    });
    await new Promise((resolve, reject) => {
      this.ws.addEventListener('open', () => {
        this.connected = true;
        this.disconnectReason = null;
        resolve();
      }, { once: true });
      this.ws.addEventListener('error', (event) => {
        const message = event?.error?.message || event?.message || 'CDP WebSocket error';
        reject(fatalCdpError(message));
      }, { once: true });
      this.ws.addEventListener('close', () => {
        reject(fatalCdpError(this.disconnectReason || 'Browser closed CDP WebSocket before connection opened'));
      }, { once: true });
    });
  }

  close() {
    this.markDisconnected('CDP connection closed by downloader');
    this.ws?.close();
  }

  markDisconnected(reason) {
    if (!this.connected && this.disconnectReason) return;
    this.connected = false;
    this.disconnectReason = reason || 'CDP disconnected';
    const error = fatalCdpError(this.disconnectReason);
    for (const [id, pending] of this.pending.entries()) {
      clearTimeout(pending.timer);
      pending.reject(error);
      this.pending.delete(id);
    }
  }

  assertConnected(context) {
    if (!this.connected || this.ws?.readyState !== WebSocket.OPEN) {
      throw fatalCdpError(`WebSocket not open for ${context}: ${this.disconnectReason || 'CDP disconnected'}`);
    }
  }

  handleMessage(event) {
    const message = JSON.parse(event.data);
    if (message.method === 'Browser.downloadWillBegin') {
      this.downloads.set(message.params.guid, {
        ...message.params,
        startedAt: Date.now(),
        state: 'willBegin',
      });
    }
    if (message.method === 'Browser.downloadProgress') {
      const current = this.downloads.get(message.params.guid) || { startedAt: Date.now() };
      this.downloads.set(message.params.guid, {
        ...current,
        ...message.params,
      });
    }
    if (message.id && this.pending.has(message.id)) {
      const pending = this.pending.get(message.id);
      clearTimeout(pending.timer);
      this.pending.delete(message.id);
      if (message.error) {
        const error = new Error(`${pending.method}: ${JSON.stringify(message.error)}`);
        if (isFatalCdpError(error)) error.fatalCdp = true;
        pending.reject(error);
      } else {
        pending.resolve(message.result || {});
      }
    }
  }

  send(method, params = {}, sessionId = null, timeoutMs = 30000) {
    return new Promise((resolve, reject) => {
      try {
        this.assertConnected(method);
      } catch (error) {
        reject(error);
        return;
      }
      const id = this.nextId++;
      const message = { id, method, params };
      if (sessionId) message.sessionId = sessionId;
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`${method} timed out`));
      }, timeoutMs);
      this.pending.set(id, { resolve, reject, timer, method });
      try {
        this.ws.send(JSON.stringify(message));
      } catch (error) {
        clearTimeout(timer);
        this.pending.delete(id);
        this.markDisconnected(error.message);
        reject(fatalCdpError(`WebSocket not open for ${method}: ${error.message}`));
      }
    });
  }

  async createPage(url = 'about:blank', background = true) {
    const { targetId } = await this.send('Target.createTarget', { url, background });
    const { sessionId } = await this.send('Target.attachToTarget', { targetId, flatten: true });
    await this.send('Page.enable', {}, sessionId);
    await this.send('Runtime.enable', {}, sessionId);
    await this.waitForLoad(sessionId);
    return { targetId, sessionId };
  }

  async closePage(targetId) {
    try {
      await this.send('Target.closeTarget', { targetId });
    } catch {
      // Non-critical cleanup.
    }
  }

  async navigate(sessionId, url) {
    await this.send('Page.navigate', { url }, sessionId);
    await this.waitForLoad(sessionId);
  }

  async waitForLoad(sessionId, timeoutMs = 30000) {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      const ready = await this.evaluate(sessionId, 'document.readyState').catch(() => null);
      if (ready === 'complete' || ready === 'interactive') return;
      await delay(300);
    }
  }

  async waitForExpression(sessionId, expression, timeoutMs = 30000) {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      const value = await this.evaluate(sessionId, expression).catch(() => false);
      if (value) return value;
      await delay(500);
    }
    throw new Error(`Timed out waiting for expression: ${expression.slice(0, 120)}`);
  }

  async evaluate(sessionId, expression, timeoutMs = 30000) {
    const result = await this.send(
      'Runtime.evaluate',
      {
        expression,
        returnByValue: true,
        awaitPromise: true,
      },
      sessionId,
      timeoutMs,
    );
    if (result.exceptionDetails) {
      throw new Error(result.exceptionDetails.text || 'Runtime.evaluate exception');
    }
    return result.result?.value;
  }

  async setDownloadPath(downloadPath) {
    await this.send('Browser.setDownloadBehavior', {
      behavior: 'allow',
      downloadPath,
      eventsEnabled: true,
    });
  }

  async trueClickSelector(targetId, sessionId, selector, prepare = '') {
    await this.send('Target.activateTarget', { targetId });
    const coord = await this.evaluate(
      sessionId,
      `(() => {
        ${prepare}
        const el = document.querySelector(${JSON.stringify(selector)});
        if (!el) return { error: 'missing selector: ${selector}' };
        el.scrollIntoView({ block: 'center', inline: 'center' });
        const rect = el.getBoundingClientRect();
        if (!rect.width || !rect.height) return { error: 'selector not visible: ${selector}' };
        return {
          x: rect.x + rect.width / 2,
          y: rect.y + rect.height / 2,
          text: (el.innerText || el.title || '').trim(),
        };
      })()`,
    );
    if (!coord || coord.error) throw new Error(coord?.error || `Cannot click ${selector}`);
    await this.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: coord.x, y: coord.y }, sessionId);
    await this.send(
      'Input.dispatchMouseEvent',
      { type: 'mousePressed', x: coord.x, y: coord.y, button: 'left', buttons: 1, clickCount: 1 },
      sessionId,
    );
    await this.send(
      'Input.dispatchMouseEvent',
      { type: 'mouseReleased', x: coord.x, y: coord.y, button: 'left', buttons: 0, clickCount: 1 },
      sessionId,
    );
    return coord;
  }

  async waitForNewDownload(previousGuids, timeoutMs = 90000) {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      this.assertConnected('download wait');
      for (const [guid, data] of this.downloads.entries()) {
        if (previousGuids.has(guid)) continue;
        if (data.state === 'completed') {
          if (data.filePath) return data.filePath;
          if (data.suggestedFilename) return path.join(TMP_DOWNLOAD_DIR, data.suggestedFilename);
        }
        if (data.state === 'canceled') {
          throw new Error('download canceled by Chrome/CNKI');
        }
      }
      await delay(500);
    }
    throw new Error('download timeout');
  }
}

async function checkLogin(cdp, sessionId) {
  const institutionPattern = process.env.CNKI_INSTITUTION_PATTERN || '';
  await cdp.navigate(sessionId, CNKI_HOME);
  if (institutionPattern) {
    await cdp.waitForExpression(
      sessionId,
      `(() => new RegExp(${JSON.stringify(institutionPattern)}).test(document.body.innerText || ''))()`,
      12000,
    ).catch(() => null);
  }
  await jitter(1000, 1500);
  const state = await cdp.evaluate(
    sessionId,
    `(() => {
      const text = document.body.innerText || '';
      const institutionPattern = ${JSON.stringify(institutionPattern)};
      return {
        institution: institutionPattern ? new RegExp(institutionPattern).test(text) : !/登录/.test(text),
        loginText: /登录/.test(text),
        sample: text.slice(0, 500)
      };
    })()`,
  );
  if (!state?.institution) {
    throw new Error(`CNKI login was not detected. Log in to CNKI in Chrome with an authorized institutional or personal account, optionally set CNKI_INSTITUTION_PATTERN to your institution text, then rerun this task. Page sample: ${state?.sample || ''}`);
  }
}

async function runSearch(cdp, sessionId, query) {
  await cdp.navigate(sessionId, CNKI_ADVANCED);
  await jitter(1200, 1800);
  const expression = cnkiExpression(query);
  await cdp.evaluate(
    sessionId,
    `(async () => {
      const fire = (el, type) => el.dispatchEvent(new Event(type, { bubbles: true }));
      const visible = (el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
      const journal = [...document.querySelectorAll('a[name=classify]')]
        .find((el) => el.getAttribute('resource') === 'JOURNAL' && visible(el));
      if (journal) {
        journal.click();
        await new Promise((resolve) => setTimeout(resolve, 300));
      }
      const boxes = [...document.querySelectorAll('input[type=text][data-tipid]')].filter(visible);
      if (!boxes.length) return { error: 'search input not found' };
      boxes.forEach((box, index) => {
        box.value = index === 0 ? ${JSON.stringify(expression)} : '';
        fire(box, 'input');
        fire(box, 'change');
      });
      const d0 = document.querySelector('#datebox0');
      const d1 = document.querySelector('#datebox1');
      const journalYearStart = document.querySelector('.tit-startend-yearbox .sort.start input');
      const journalYearEnd = document.querySelector('.tit-startend-yearbox .sort.end input');
      if (journalYearStart && journalYearEnd) {
        journalYearStart.value = ${JSON.stringify(String(query.year_from))};
        journalYearEnd.value = ${JSON.stringify(String(query.year_to))};
        fire(journalYearStart, 'input');
        fire(journalYearStart, 'change');
        fire(journalYearEnd, 'input');
        fire(journalYearEnd, 'change');
      } else {
        if (d0) {
          d0.removeAttribute('readonly');
          d0.value = ${JSON.stringify(`${query.year_from}-01-01`)};
          fire(d0, 'input');
          fire(d0, 'change');
        }
        if (d1) {
          d1.removeAttribute('readonly');
          d1.value = ${JSON.stringify(`${query.year_to}-12-31`)};
          fire(d1, 'input');
          fire(d1, 'change');
        }
      }
      const relevance = document.querySelector('input[name=order][value=FFD], #FFD');
      if (relevance) relevance.checked = true;
      const button = document.querySelector('input.btn-search, input.search-btn, button.btn-search');
      if (!button) return { error: 'search button not found' };
      button.click();
      return { ok: true, expression: ${JSON.stringify(expression)} };
    })()`,
  );
  await cdp.waitForExpression(
    sessionId,
    `(() => /共找到\\s*[\\d,]+\\s*条结果|未找到|暂无数据/.test(document.body.innerText || ''))()`,
    45000,
  );
  await cdp.evaluate(
    sessionId,
    `(() => {
      const relevance = document.querySelector('#sortList li#FFD');
      if (relevance && !/cur/.test(relevance.className || '')) {
        relevance.click();
        return true;
      }
      return false;
    })()`,
  );
  await cdp.waitForExpression(
    sessionId,
    `(() => {
      const item = document.querySelector('#sortList li#FFD');
      if (!item) return true;
      return /cur/.test(item.className || '');
    })()`,
    20000,
  );
  await jitter(1500, 2200);
  return cdp.evaluate(
    sessionId,
    `(() => {
      const text = document.body.innerText || '';
      return {
        total: (${parseResultTotal.toString()})(text),
        url: location.href,
        text: text.slice(0, 1200)
      };
    })()`,
  );
}

async function collectPageResults(cdp, sessionId, queryId) {
  return cdp.evaluate(
    sessionId,
    `(() => {
      const clean = (value) => String(value || '').replace(/\\s+/g, ' ').trim();
      return [...document.querySelectorAll('table.result-table-list tbody tr')].map((row, index) => {
        const titleLink = row.querySelector('td.name a.fz14');
        const collect = row.querySelector('td.operat a.icon-collect');
        const date = clean(row.querySelector('td.date')?.innerText);
        const yearMatch = date.match(/(\\d{4})/);
        const authors = clean(row.querySelector('td.author')?.innerText)
          .split(/[;；、,，]/)
          .map((item) => clean(item))
          .filter(Boolean);
        return {
          query_id: ${JSON.stringify(queryId)},
          rank: index + 1,
          title: clean(titleLink?.innerText),
          authors,
          journal: clean(row.querySelector('td.source')?.innerText),
          year: yearMatch ? Number(yearMatch[1]) : 0,
          date,
          doi_or_cnki_id: collect?.getAttribute('data-filename') || '',
          url: titleLink?.href || '',
          hasDownload: !!row.querySelector('td.operat a.downloadlink.icon-download, td.operat a[title="下载"]'),
        };
      }).filter((item) => item.title && item.url);
    })()`,
  );
}

async function clickNextPage(cdp, sessionId) {
  const before = await cdp.evaluate(
    sessionId,
    `document.querySelector('table.result-table-list tbody tr a.fz14')?.innerText || ''`,
  );
  const clicked = await cdp.evaluate(
    sessionId,
    `(() => {
      const links = [...document.querySelectorAll('a')];
      const next = links.find((a) => /下一页/.test((a.innerText || a.title || '').trim()));
      if (!next) return false;
      if (/disabled|disable/.test(next.className || '')) return false;
      next.scrollIntoView({ block: 'center' });
      next.click();
      return true;
    })()`,
  );
  if (!clicked) return false;
  const start = Date.now();
  while (Date.now() - start < 20000) {
    await delay(600);
    const after = await cdp.evaluate(
      sessionId,
      `document.querySelector('table.result-table-list tbody tr a.fz14')?.innerText || ''`,
    ).catch(() => '');
    if (after && after !== before) {
      await jitter(1000, 1600);
      return true;
    }
  }
  return false;
}

async function readDetailMetadata(cdp, sessionId, fallback) {
  const detail = await cdp.evaluate(
    sessionId,
    `(() => {
      const clean = (value) => String(value || '').replace(/\\s+/g, ' ').trim();
      const ownText = (el) => el ? [...el.childNodes]
        .filter((node) => node.nodeType === Node.TEXT_NODE)
        .map((node) => node.textContent)
        .join(' ') : '';
      const body = document.body.innerText || '';
      const title = clean(ownText(document.querySelector('.wx-tit h1')) || document.querySelector('.wx-tit h1')?.innerText);
      const authors = [...document.querySelectorAll('#authorpart a')]
        .map((a) => clean(ownText(a) || a.innerText).replace(/\\d+$/g, ''))
        .filter(Boolean);
      const topTip = clean(document.querySelector('.doc-top .top-tip')?.innerText);
      const journal = clean(document.querySelector('.doc-top .top-tip a')?.innerText).replace(/[.。]$/g, '');
      const yearMatch = topTip.match(/(20\\d{2}|19\\d{2})/);
      const doi = body.match(/DOI：\\s*([^\\n]+)/)?.[1] || body.match(/DOI:\\s*([^\\n]+)/)?.[1] || '';
      const abstract = clean(document.querySelector('#ChDivSummary, .abstract-text')?.innerText);
      const keywords = [...document.querySelectorAll('p.keywords a, .keywords a')]
        .map((a) => clean(a.innerText).replace(/[;；,，]+$/g, ''))
        .filter(Boolean);
      return {
        title,
        authors,
        journal,
        year: yearMatch ? Number(yearMatch[1]) : 0,
        doi_or_cnki_id: clean(doi),
        abstract,
        keywords,
        url: location.href,
        hasPdf: !!document.querySelector('#pdfDown'),
      };
    })()`,
  );
  return {
    ...fallback,
    ...Object.fromEntries(Object.entries(detail || {}).filter(([, value]) => {
      if (Array.isArray(value)) return value.length > 0;
      return value !== undefined && value !== null && value !== '' && value !== 0;
    })),
    doi_or_cnki_id: detail?.doi_or_cnki_id || fallback.doi_or_cnki_id || '',
    url: detail?.url || fallback.url,
  };
}

async function downloadDetailPdf(cdp, detailTargetId, detailSessionId, targetPdf) {
  const previousGuids = new Set(cdp.downloads.keys());
  await cdp.trueClickSelector(
    detailTargetId,
    detailSessionId,
    '#pdfDown',
    `const pdf = document.querySelector('#pdfDown'); if (pdf) pdf.setAttribute('target', '_self');`,
  );
  const downloadedPath = assertSafeDownloadedPdfPath(await cdp.waitForNewDownload(previousGuids));
  const safeTargetPdf = assertSafeTargetPdfPath(targetPdf);
  if (!isPdf(downloadedPath)) {
    const badPath = `${downloadedPath}.not-pdf`;
    fs.renameSync(downloadedPath, badPath);
    throw new Error(`downloaded file is not a PDF: ${path.basename(badPath)}`);
  }
  fs.renameSync(downloadedPath, safeTargetPdf);
  if (!isPdf(safeTargetPdf)) throw new Error('renamed file failed PDF validation');
}

function writeProvenance(sourceId, queryId, metadata) {
  ensureDirs();
  const data = {
    source_id: sourceId,
    query_id: queryId,
    db: 'cnki',
    title: metadata.title || '',
    authors: metadata.authors || [],
    journal: metadata.journal || '',
    year: metadata.year || 0,
    doi_or_cnki_id: metadata.doi_or_cnki_id || '',
    url: metadata.url || '',
    abstract: metadata.abstract || '',
    keywords: metadata.keywords || [],
    download_status: 'success',
    downloaded_at: isoNow(),
  };
  fs.writeFileSync(path.join(PROVENANCE_DIR, `${sourceId}.json`), JSON.stringify(data, null, 2), 'utf8');
}

function writeManifest(manifest) {
  ensureDirs();
  fs.writeFileSync(MANIFEST_PATH, JSON.stringify(manifest, null, 2), 'utf8');
}

async function main() {
  ensureDirs();
  cleanupTmpDownloads();

  const taskText = fs.readFileSync(TASK_PATH, 'utf8');
  const queries = parseQueries(taskText);
  const manifestId = `download_manifest_${new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14)}`;
  const createdAt = isoNow();
  const queriesExecuted = [];
  const failedDownloads = [];
  let totalFound = 0;
  let totalDownloaded = 0;

  const buildManifest = (extra = {}) => ({
    manifest_id: manifestId,
    created_at: createdAt,
    task_type: 'cnki_search_download',
    queries_executed: queriesExecuted,
    total_found: totalFound,
    total_downloaded: totalDownloaded,
    failed_downloads: failedDownloads,
    output_dir: 'raw-library/papers/',
    provenance_dir: 'raw-library/provenance/',
    ...extra,
  });

  if (queries.length === 0) {
    const error = new Error('No executable CNKI queries were parsed from task file');
    writeManifest(buildManifest({
      run_status: 'failed',
      fatal_error: error.message,
      stopped_at: isoNow(),
    }));
    throw error;
  }

  const cdp = new Cdp(readChromeEndpoint());
  let searchPage = null;
  let detailPage = null;
  let fatalError = null;

  try {
    await cdp.connect();
    await cdp.setDownloadPath(TMP_DOWNLOAD_DIR);

    searchPage = await cdp.createPage('about:blank', false);
    const seenTitles = existingTitleKeys();
    const attemptedTitles = new Set(seenTitles);
    const counters = nextCountersFromDisk();

    await checkLogin(cdp, searchPage.sessionId);

    for (const query of queries) {
      queriesExecuted.push(query.query_id);
      console.log(`\n[query] ${query.query_id}: ${cnkiExpression(query)}`);
      const resultInfo = await runSearch(cdp, searchPage.sessionId, query);
      totalFound += resultInfo.total || 0;
      console.log(`[query] found ${resultInfo.total || 0}`);

      let pageNo = 1;
      let queryDownloaded = 0;
      while (true) {
        const rows = await collectPageResults(cdp, searchPage.sessionId, query.query_id);
        console.log(`[page] ${query.query_id} page ${pageNo}: ${rows.length} rows`);

        for (const row of rows) {
          const key = titleKey(row.title, row.year);
          if (attemptedTitles.has(key)) continue;
          attemptedTitles.add(key);

          if (totalDownloaded >= MAX_DOWNLOADS || queryDownloaded >= PER_QUERY_SUCCESS_CAP) continue;

          const sourceId = nextSourceId(row.year || new Date().getFullYear(), counters);
          const targetPdf = path.join(PAPERS_DIR, `${sourceId}.pdf`);
          console.log(`[download] ${sourceId} ${row.title}`);

          try {
            detailPage = await cdp.createPage('about:blank', false);
            await cdp.navigate(detailPage.sessionId, row.url);
            await jitter(1300, 2100);
            const metadata = await readDetailMetadata(cdp, detailPage.sessionId, row);
            if (!metadata.hasPdf) throw new Error('PDF下载 button not found on detail page');
            await downloadDetailPdf(cdp, detailPage.targetId, detailPage.sessionId, targetPdf);
            writeProvenance(sourceId, query.query_id, metadata);
            totalDownloaded += 1;
            queryDownloaded += 1;
            seenTitles.add(key);
            console.log(`[ok] ${sourceId}`);
            await jitter(2000, 3000);
          } catch (error) {
            fs.rmSync(targetPdf, { force: true });
            if (isFatalCdpError(error)) {
              fatalError = error;
              console.log(`[fatal] ${error.message}`);
              break;
            }
            failedDownloads.push({ source_id: sourceId, reason: error.message });
            console.log(`[fail] ${sourceId}: ${error.message}`);
            await jitter(1200, 2000);
          } finally {
            cleanupTmpDownloads();
            if (detailPage) {
              await cdp.closePage(detailPage.targetId).catch(() => {});
              detailPage = null;
            }
            writeManifest(buildManifest(
              fatalError
                ? { run_status: 'failed', fatal_error: fatalError.message, stopped_at: isoNow() }
                : {},
            ));
          }
          if (fatalError) break;
        }
        if (fatalError) break;

        const shouldContinue = totalDownloaded < MAX_DOWNLOADS && queryDownloaded < PER_QUERY_SUCCESS_CAP;
        if (!shouldContinue) break;
        const hasNext = await clickNextPage(cdp, searchPage.sessionId);
        if (!hasNext) break;
        pageNo += 1;
      }
      if (fatalError) break;
    }
  } catch (error) {
    if (!isFatalCdpError(error)) throw error;
    fatalError = error;
    console.log(`[fatal] ${error.message}`);
    writeManifest(buildManifest({
      run_status: 'failed',
      fatal_error: fatalError.message,
      stopped_at: isoNow(),
    }));
  } finally {
    if (detailPage) await cdp.closePage(detailPage.targetId).catch(() => {});
    if (searchPage) await cdp.closePage(searchPage.targetId).catch(() => {});
    cdp.close();
  }

  if (fatalError) {
    writeManifest(buildManifest({
      run_status: 'failed',
      fatal_error: fatalError.message,
      stopped_at: isoNow(),
    }));
    throw fatalError;
  }

  const manifest = buildManifest({
    run_status: 'completed',
  });
  writeManifest(manifest);
  console.log(`\n[done] found=${totalFound} downloaded=${totalDownloaded} failed=${failedDownloads.length}`);
}

main().catch((error) => {
  console.error(`[fatal] ${error.stack || error.message}`);
  process.exitCode = 1;
});
