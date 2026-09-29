export interface VideoItem {
  id: string;
  url: string;
  title: string;
  thumbnail?: string;
  duration?: string;
  availableResolution: number; // e.g. 1080, 2160
  chosenClient: string; // e.g. "ios", "android", "tv"
  driveStatus: 'not_synced' | 'synced' | 'upgrade_available' | 'in_progress';
  existingDriveFileId?: string;
  existingDriveResolution?: number;
  existingDriveName?: string;
  fileSizeMb?: number;
}

export interface DriveFile {
  id: string;
  name: string;
  videoId?: string;
  resolution: number;
  size: number;
  createdTime: string;
  webViewLink?: string;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: 'INFO' | 'WARNING' | 'ERROR' | 'SUCCESS';
  message: string;
}

export interface SyncConfig {
  youtubeUrl: string;
  targetFolderId: string;
  updateExisting: boolean;
  forceQualityLimit: number;
  hasCookies: boolean;
  hasDriveCredentials: boolean;
  scheduleIntervalHours: number;
  autoSyncEnabled: boolean;
}

export interface SyncStats {
  totalSynced: number;
  totalUpgraded: number;
  totalSkipped: number;
  totalErrors: number;
  lastRunTime?: string;
  isRunning: boolean;
  progressPercent: number;
  currentVideoTitle?: string;
}
