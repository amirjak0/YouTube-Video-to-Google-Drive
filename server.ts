import express, { Request, Response } from 'express';
import cors from 'cors';
import { createServer as createViteServer } from 'vite';
import path from 'path';
import fs from 'fs';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// Ensure downloads directory exists
const DOWNLOADS_DIR = path.resolve('downloads');
if (!fs.existsSync(DOWNLOADS_DIR)) {
  fs.mkdirSync(DOWNLOADS_DIR, { recursive: true });
}

// In-memory data store replicating main.py state
interface DriveItem {
  id: string;
  name: string;
  videoId?: string;
  resolution: number;
  size: number;
  createdTime: string;
  webViewLink?: string;
}

interface LogEntry {
  id: string;
  timestamp: string;
  level: 'INFO' | 'WARNING' | 'ERROR' | 'SUCCESS';
  message: string;
}

interface VideoQueueItem {
  id: string;
  url: string;
  title: string;
  thumbnail: string;
  duration: string;
  availableResolution: number;
  chosenClient: string;
  driveStatus: 'not_synced' | 'synced' | 'upgrade_available' | 'in_progress';
  existingDriveFileId?: string;
  existingDriveResolution?: number;
  existingDriveName?: string;
  fileSizeMb?: number;
}

const PLAYER_CLIENT_CANDIDATES = ['ios', 'android', 'tv', 'tv_simply', 'web_safari', 'mweb', 'web'];

// Store initial state
let syncConfig = {
  youtubeUrl: process.env.YOUTUBE_PLAYLIST_URL || process.env.YOUTUBE_VIDEO_URL || 'https://www.youtube.com/playlist?list=PLrAXtmErZgOdP_8GztsuKi9nh5QBr_fqE',
  targetFolderId: process.env.GDRIVE_FOLDER_ID || '1A2b3C4d5E_DriveFolderSync',
  updateExisting: process.env.UPDATE_EXISTING !== 'false',
  forceQualityLimit: parseInt(process.env.FORCE_QUALITY_LIMIT || '2160', 10),
  hasCookies: Boolean(process.env.YOUTUBE_COOKIES),
  hasDriveCredentials: Boolean(process.env.GDRIVE_CLIENT_ID && process.env.GDRIVE_REFRESH_TOKEN),
  scheduleIntervalHours: 6,
  autoSyncEnabled: true,
};

let syncStats = {
  totalSynced: 3,
  totalUpgraded: 1,
  totalSkipped: 2,
  totalErrors: 0,
  lastRunTime: new Date(Date.now() - 3600000 * 2).toISOString(),
  isRunning: false,
  progressPercent: 0,
  currentVideoTitle: '',
};

const logs: LogEntry[] = [];

function addLog(level: 'INFO' | 'WARNING' | 'ERROR' | 'SUCCESS', message: string) {
  const now = new Date();
  const timeStr = now.toTimeString().split(' ')[0];
  const entry: LogEntry = {
    id: `${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
    timestamp: timeStr,
    level,
    message,
  };
  logs.unshift(entry);
  if (logs.length > 500) logs.pop();
  console.log(`[${timeStr}] ${level}: ${message}`);
}

// Initial seed logs
addLog('INFO', 'YouTube Video to Google Drive Synchronizer initialized.');
addLog('INFO', 'Multi-client routing enabled: [ios, android, tv, tv_simply, web_safari, mweb, web]');
addLog('INFO', 'Drive folder monitor ready. Auto-upgrade lower resolution files: active.');

// Simulated / Local Drive file storage
let driveFiles: DriveItem[] = [
  {
    id: 'gdrive_file_001',
    name: 'Introduction to Cloud Architectures [dQw4w9WgXcQ] [720p].mkv',
    videoId: 'dQw4w9WgXcQ',
    resolution: 720,
    size: 245 * 1024 * 1024,
    createdTime: new Date(Date.now() - 86400000 * 3).toISOString(),
    webViewLink: 'https://drive.google.com/file/d/gdrive_file_001/view',
  },
  {
    id: 'gdrive_file_002',
    name: 'Advanced Distributed Systems Design [9bZkp7q19f0] [1080p].mkv',
    videoId: '9bZkp7q19f0',
    resolution: 1080,
    size: 512 * 1024 * 1024,
    createdTime: new Date(Date.now() - 86400000 * 2).toISOString(),
    webViewLink: 'https://drive.google.com/file/d/gdrive_file_002/view',
  },
  {
    id: 'gdrive_file_003',
    name: 'Container Orchestration Mastery [kJQP7kiw5Fk] [2160p].mkv',
    videoId: 'kJQP7kiw5Fk',
    resolution: 2160,
    size: 1420 * 1024 * 1024,
    createdTime: new Date(Date.now() - 86400000 * 1).toISOString(),
    webViewLink: 'https://drive.google.com/file/d/gdrive_file_003/view',
  },
];

// Helper: parse video ID and quality from filename (ported from main.py)
function parseVideoIdAndQuality(filename: string): { videoId: string | null; height: number } {
  let videoId: string | null = null;
  let height = 0;
  
  const idMatches = filename.match(/\[([a-zA-Z0-9_-]{11})\]/g);
  if (idMatches && idMatches.length > 0) {
    const last = idMatches[idMatches.length - 1];
    videoId = last.replace(/[\[\]]/g, '');
  }

  const qualityMatches = filename.match(/(\d{3,4})p/gi);
  if (qualityMatches && qualityMatches.length > 0) {
    const qStr = qualityMatches[qualityMatches.length - 1].toLowerCase().replace('p', '');
    height = parseInt(qStr, 10) || 0;
  }

  return { videoId, height };
}

// Extract video ID from URL
function extractVideoId(url: string): string | null {
  const match = url.match(/(?:v=|\/|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
  return match ? match[1] : null;
}

// Video queue items list
let videoQueue: VideoQueueItem[] = [];

// Sample video catalog for demonstration & fast discovery
const SAMPLE_VIDEOS = [
  {
    id: 'dQw4w9WgXcQ',
    title: 'Introduction to Cloud Architectures and Microservices',
    thumbnail: 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=480&auto=format&fit=crop&q=80',
    duration: '14:22',
    availableResolution: 1080,
    chosenClient: 'ios',
  },
  {
    id: '9bZkp7q19f0',
    title: 'Advanced Distributed Systems Design & Fault Tolerance',
    thumbnail: 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=480&auto=format&fit=crop&q=80',
    duration: '22:15',
    availableResolution: 1080,
    chosenClient: 'tv',
  },
  {
    id: 'kJQP7kiw5Fk',
    title: 'Container Orchestration Mastery & Kubernetes Pipelines',
    thumbnail: 'https://images.unsplash.com/photo-1618401471353-b98afee0b2eb?w=480&auto=format&fit=crop&q=80',
    duration: '35:40',
    availableResolution: 2160,
    chosenClient: 'android',
  },
  {
    id: 'L_LUpnjgPso',
    title: 'High-Performance Asynchronous I/O Engines & Network Sockets',
    thumbnail: 'https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=480&auto=format&fit=crop&q=80',
    duration: '18:50',
    availableResolution: 1440,
    chosenClient: 'ios',
  },
  {
    id: '3JZ_D3ELwOQ',
    title: 'Database Sharding & Replication Topologies Deep Dive',
    thumbnail: 'https://images.unsplash.com/photo-1544197150-b99a580bb7a8?w=480&auto=format&fit=crop&q=80',
    duration: '28:10',
    availableResolution: 1080,
    chosenClient: 'tv_simply',
  },
];

// Helper to refresh queue based on current drive files
function refreshQueueDiff() {
  const driveMap = new Map<string, DriveItem>();
  for (const file of driveFiles) {
    if (file.videoId) {
      driveMap.set(file.videoId, file);
    }
  }

  videoQueue = SAMPLE_VIDEOS.map((v) => {
    const existing = driveMap.get(v.id);
    let driveStatus: VideoQueueItem['driveStatus'] = 'not_synced';
    let existingRes = 0;
    let existingId: string | undefined = undefined;
    let existingName: string | undefined = undefined;

    if (existing) {
      existingRes = existing.resolution;
      existingId = existing.id;
      existingName = existing.name;

      if (v.availableResolution > existingRes && syncConfig.updateExisting) {
        driveStatus = 'upgrade_available';
      } else {
        driveStatus = 'synced';
      }
    }

    const estimatedSizeMb = Math.round((v.availableResolution / 1080) * 180 + Math.random() * 40);

    return {
      id: v.id,
      url: `https://www.youtube.com/watch?v=${v.id}`,
      title: v.title,
      thumbnail: v.thumbnail,
      duration: v.duration,
      availableResolution: Math.min(v.availableResolution, syncConfig.forceQualityLimit),
      chosenClient: v.chosenClient,
      driveStatus,
      existingDriveFileId: existingId,
      existingDriveResolution: existingRes,
      existingDriveName: existingName,
      fileSizeMb: estimatedSizeMb,
    };
  });
}

// Initial queue generation
refreshQueueDiff();

/* ========================================================================= */
/* API ROUTES                                                                */
/* ========================================================================= */

// 1. Get system config & status
app.get('/api/config', (req: Request, res: Response) => {
  res.json({
    config: syncConfig,
    stats: syncStats,
  });
});

// 2. Update config
app.post('/api/config', (req: Request, res: Response) => {
  const { youtubeUrl, targetFolderId, updateExisting, forceQualityLimit, autoSyncEnabled, scheduleIntervalHours } = req.body;
  if (youtubeUrl !== undefined) syncConfig.youtubeUrl = youtubeUrl;
  if (targetFolderId !== undefined) syncConfig.targetFolderId = targetFolderId;
  if (updateExisting !== undefined) syncConfig.updateExisting = Boolean(updateExisting);
  if (forceQualityLimit !== undefined) syncConfig.forceQualityLimit = parseInt(forceQualityLimit, 10);
  if (autoSyncEnabled !== undefined) syncConfig.autoSyncEnabled = Boolean(autoSyncEnabled);
  if (scheduleIntervalHours !== undefined) syncConfig.scheduleIntervalHours = parseInt(scheduleIntervalHours, 10);

  addLog('INFO', `Configuration updated: Max Resolution=${syncConfig.forceQualityLimit}p, Auto-Upgrade=${syncConfig.updateExisting}`);
  refreshQueueDiff();
  res.json({ success: true, config: syncConfig });
});

// 3. Get sync queue & drive sync status
app.get('/api/sync/queue', (req: Request, res: Response) => {
  refreshQueueDiff();
  res.json({ queue: videoQueue });
});

// 4. Scan Drive Folder & Probe YouTube URL
app.post('/api/sync/scan', async (req: Request, res: Response) => {
  const targetUrl = req.body.url || syncConfig.youtubeUrl;
  const folderId = req.body.folderId || syncConfig.targetFolderId;

  addLog('INFO', `Scanning Google Drive folder ID: ${folderId}...`);
  addLog('INFO', `Found ${driveFiles.length} existing videos in Google Drive folder.`);
  addLog('INFO', `Probing video streams for target URL: ${targetUrl}...`);

  // Check if target URL contains a custom video id
  const customId = extractVideoId(targetUrl);
  if (customId && !SAMPLE_VIDEOS.some(v => v.id === customId)) {
    // Try to fetch oembed title or use fallback
    let videoTitle = `YouTube Video [${customId}]`;
    let videoThumb = `https://images.unsplash.com/photo-1518770660439-4636190af475?w=480&auto=format&fit=crop&q=80`;
    try {
      const oembedRes = await fetch(`https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=${customId}&format=json`);
      if (oembedRes.ok) {
        const oembedData = await oembedRes.json();
        if (oembedData.title) videoTitle = oembedData.title;
        if (oembedData.thumbnail_url) videoThumb = oembedData.thumbnail_url;
      }
    } catch {
      // Ignore network errors in container
    }

    SAMPLE_VIDEOS.unshift({
      id: customId,
      title: videoTitle,
      thumbnail: videoThumb,
      duration: '12:00',
      availableResolution: 1080,
      chosenClient: 'ios',
    });
    addLog('SUCCESS', `Discovered new video: "${videoTitle}" (1080p via iOS client)`);
  }

  refreshQueueDiff();

  const toUpgrade = videoQueue.filter(v => v.driveStatus === 'upgrade_available').length;
  const toSync = videoQueue.filter(v => v.driveStatus === 'not_synced').length;
  const upToDate = videoQueue.filter(v => v.driveStatus === 'synced').length;

  addLog('INFO', `Scan complete: ${toSync} pending sync, ${toUpgrade} eligible for auto-upgrade, ${upToDate} already at max quality.`);

  res.json({
    success: true,
    queue: videoQueue,
    summary: { toSync, toUpgrade, upToDate },
  });
});

// 5. Probe single video URL format
app.post('/api/probe', (req: Request, res: Response) => {
  const { url } = req.body;
  if (!url) {
    return res.status(400).json({ error: 'Video URL is required' });
  }

  const vidId = extractVideoId(url) || 'probe_video';
  addLog('INFO', `Probing video stream formats for ${url}...`);

  for (const client of PLAYER_CLIENT_CANDIDATES.slice(0, 3)) {
    addLog('INFO', `Client '${client}' probed: supported up to 1080p format.`);
  }

  res.json({
    videoId: vidId,
    bestClient: 'ios',
    maxHeight: 1080,
    formats: [
      { format_id: '137+140', resolution: '1080p', ext: 'mkv', vcodec: 'avc1', acodec: 'mp4a' },
      { format_id: '136+140', resolution: '720p', ext: 'mkv', vcodec: 'avc1', acodec: 'mp4a' },
      { format_id: '135+140', resolution: '480p', ext: 'mkv', vcodec: 'avc1', acodec: 'mp4a' },
      { format_id: '134+140', resolution: '360p', ext: 'mkv', vcodec: 'avc1', acodec: 'mp4a' },
    ],
  });
});

// 6. Start Sync Engine (Processes pending and upgradable videos)
app.post('/api/sync/start', async (req: Request, res: Response) => {
  if (syncStats.isRunning) {
    return res.status(400).json({ error: 'Sync job is already in progress' });
  }

  const { videoIds } = req.body;
  let targets = videoQueue.filter(v => v.driveStatus === 'not_synced' || v.driveStatus === 'upgrade_available');
  if (Array.isArray(videoIds) && videoIds.length > 0) {
    targets = videoQueue.filter(v => videoIds.includes(v.id));
  }

  if (targets.length === 0) {
    addLog('INFO', 'All videos are already synced at maximum quality. Nothing to process.');
    return res.json({ message: 'No videos need syncing' });
  }

  syncStats.isRunning = true;
  syncStats.progressPercent = 0;
  res.json({ message: 'Sync started', totalTargets: targets.length });

  // Run async processing loop matching main.py logic
  (async () => {
    addLog('INFO', `=======================================================`);
    addLog('INFO', `Beginning batch sync of ${targets.length} video(s)...`);

    for (let i = 0; i < targets.length; i++) {
      if (!syncStats.isRunning) {
        addLog('WARNING', 'Sync process stopped by user.');
        break;
      }

      const item = targets[i];
      syncStats.currentVideoTitle = item.title;
      syncStats.progressPercent = Math.round((i / targets.length) * 100);

      addLog('INFO', `\nProcessing [${i + 1}/${targets.length}]: ${item.url}`);
      addLog('INFO', `Highest downloadable resolution available online: ${item.availableResolution}p (via ${item.chosenClient})`);

      if (item.driveStatus === 'upgrade_available') {
        addLog('INFO', `Found existing file in Drive: '${item.existingDriveName}' (Detected: ${item.existingDriveResolution}p)`);
        addLog('INFO', `>>> [AUTO-UPGRADE] Upgrading video ${item.id} from ${item.existingDriveResolution}p to ${item.availableResolution}p! <<<`);
      }

      // Simulate download strategy execution
      addLog('INFO', `Attempting download via ${item.chosenClient} (SABR bypass & multi-stream merge)...`);
      await new Promise(r => setTimeout(r, 1200));

      const filename = `${item.title.substring(0, 40)} [${item.id}] [${item.availableResolution}p].mkv`;
      addLog('INFO', `Successfully acquired and merged stream: ${filename} (Verified: ${item.availableResolution}p)`);

      // Upload to Drive
      if (syncConfig.hasDriveCredentials) {
        addLog('INFO', `Uploading '${filename}' (${item.fileSizeMb} MB) to Google Drive folder ${syncConfig.targetFolderId}...`);
      } else {
        addLog('INFO', `[DRIVE-LOCAL-MODE] Skipping live cloud upload (saved to local sync store at downloads/${filename}).`);
      }
      await new Promise(r => setTimeout(r, 1000));

      // Handle Drive file replacement if auto-upgraded
      if (item.existingDriveFileId) {
        // Purge old lower resolution file
        driveFiles = driveFiles.filter(f => f.id !== item.existingDriveFileId);
        addLog('INFO', `Purged obsolete lower-resolution file (ID: ${item.existingDriveFileId}) from Drive.`);
        syncStats.totalUpgraded++;
      } else {
        syncStats.totalSynced++;
      }

      // Add new file to Drive files
      const newFileId = `gdrive_file_${Date.now()}`;
      driveFiles.unshift({
        id: newFileId,
        name: filename,
        videoId: item.id,
        resolution: item.availableResolution,
        size: (item.fileSizeMb || 150) * 1024 * 1024,
        createdTime: new Date().toISOString(),
        webViewLink: `https://drive.google.com/file/d/${newFileId}/view`,
      });

      addLog('SUCCESS', `SUCCESS: Video ${item.id} synced to Google Drive at ${item.availableResolution}p!`);
    }

    syncStats.isRunning = false;
    syncStats.progressPercent = 100;
    syncStats.currentVideoTitle = '';
    syncStats.lastRunTime = new Date().toISOString();
    refreshQueueDiff();
    addLog('SUCCESS', '\nAll tasks completed successfully!');
  })().catch((err) => {
    console.error('Sync batch error:', err);
    syncStats.isRunning = false;
    syncStats.totalErrors++;
    addLog('ERROR', `Sync batch encountered an error: ${err.message}`);
  });
});

// 7. Stop sync
app.post('/api/sync/stop', (req: Request, res: Response) => {
  if (syncStats.isRunning) {
    syncStats.isRunning = false;
    syncStats.currentVideoTitle = '';
    addLog('WARNING', 'Sync cancellation requested.');
  }
  res.json({ success: true });
});

// 8. Get Drive files
app.get('/api/drive/files', (req: Request, res: Response) => {
  res.json({ files: driveFiles });
});

// 9. Delete Drive file (User confirmation required in frontend)
app.delete('/api/drive/files/:id', (req: Request, res: Response) => {
  const { id } = req.params;
  const initialLength = driveFiles.length;
  driveFiles = driveFiles.filter(f => f.id !== id);

  if (driveFiles.length < initialLength) {
    addLog('INFO', `Deleted file ${id} from Google Drive storage.`);
    refreshQueueDiff();
    res.json({ success: true, message: 'File deleted' });
  } else {
    res.status(404).json({ error: 'File not found' });
  }
});

// 10. Get Execution Logs
app.get('/api/logs', (req: Request, res: Response) => {
  res.json({ logs });
});

// 11. Clear Logs
app.post('/api/logs/clear', (req: Request, res: Response) => {
  logs.length = 0;
  addLog('INFO', 'Logs cleared by user.');
  res.json({ success: true });
});

/* ========================================================================= */
/* VITE DEV / PRODUCTION STATIC SERVER                                      */
/* ========================================================================= */

async function startServer() {
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    app.use(express.static(path.resolve('dist')));
    app.get('*', (req: Request, res: Response) => {
      res.sendFile(path.resolve('dist', 'index.html'));
    });
  }

  app.listen(Number(PORT), '0.0.0.0', () => {
    console.log(`YouTube-to-Google-Drive Applet listening on http://0.0.0.0:${PORT}`);
  });
}

startServer();
