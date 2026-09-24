export interface DriveFileItem {
  id: string;
  name: string;
  videoId: string | null;
  height: number;
  size: number;
  createdTime: string;
  driveUrl?: string;
}

export interface ClientProbeResult {
  client: string;
  maxHeight: number;
  width: number;
  fps: number;
  formatId: string;
  status: 'available' | 'blocked' | 'limited';
}

export interface VideoMetadata {
  id: string;
  url: string;
  title: string;
  author: string;
  thumbnail: string;
  duration?: string;
  probedQualities: ClientProbeResult[];
  bestHeight: number;
  bestClient: string;
  bestFormatId: string;
  driveStatus: 'synced_current' | 'upgrade_available' | 'missing';
  currentDriveHeight?: number;
  currentDriveFileId?: string;
}

export interface SyncJob {
  id: string;
  playlistUrl?: string;
  startTime: string;
  endTime?: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  totalVideos: number;
  processedVideos: number;
  successCount: number;
  upgradedCount: number;
  skippedCount: number;
  failedCount: number;
  logs: Array<{ time: string; level: 'info' | 'warn' | 'error' | 'success'; message: string }>;
  currentVideoTitle?: string;
}

export interface SystemStatus {
  appName: string;
  status: string;
  driveConnected: boolean;
  driveMode: 'google_workspace_oauth' | 'simulated_local_vault';
  folderId: string;
  updateExisting: boolean;
  maxResolution: number;
  activeJobsCount: number;
  totalFilesTracked: number;
  cronSchedule?: string;
  nextCronRun?: string;
  lastCronRun?: string;
}
