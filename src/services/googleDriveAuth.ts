import { initializeApp, getApps } from 'firebase/app';
import {
  getAuth,
  signInWithPopup,
  GoogleAuthProvider,
  onAuthStateChanged,
  signOut,
  User
} from 'firebase/auth';
import firebaseConfig from '../../firebase-applet-config.json';

const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0];
export const auth = getAuth(app);

const provider = new GoogleAuthProvider();
provider.addScope('https://www.googleapis.com/auth/drive');
provider.setCustomParameters({
  prompt: 'select_account'
});

let isSigningIn = false;
let cachedAccessToken: string | null = null;

export const initAuth = (
  onAuthSuccess?: (user: User, token: string) => void,
  onAuthFailure?: () => void
) => {
  return onAuthStateChanged(auth, async (user: User | null) => {
    if (user) {
      if (cachedAccessToken) {
        if (onAuthSuccess) onAuthSuccess(user, cachedAccessToken);
      } else if (!isSigningIn) {
        // Token was cleared on page reload; user is signed in to Firebase but needs fresh OAuth credential popup
        if (onAuthFailure) onAuthFailure();
      }
    } else {
      cachedAccessToken = null;
      if (onAuthFailure) onAuthFailure();
    }
  });
};

export const googleSignIn = async (): Promise<{ user: User; accessToken: string } | null> => {
  try {
    isSigningIn = true;
    const result = await signInWithPopup(auth, provider);
    const credential = GoogleAuthProvider.credentialFromResult(result);
    if (!credential?.accessToken) {
      throw new Error('توکن دسترسی گوگل درایو دریافت نشد.');
    }

    cachedAccessToken = credential.accessToken;
    return { user: result.user, accessToken: cachedAccessToken };
  } catch (error: any) {
    console.error('Drive Google Sign In error:', error);
    throw error;
  } finally {
    isSigningIn = false;
  }
};

export const getAccessToken = (): string | null => {
  return cachedAccessToken;
};

export const googleSignOut = async () => {
  await signOut(auth);
  cachedAccessToken = null;
};

// Drive API Helpers using the user's direct OAuth Access Token
export async function fetchDriveFilesWithToken(accessToken: string, folderId?: string) {
  let query = "trashed = false and mimeType != 'application/vnd.google-apps.folder'";
  if (folderId) {
    query = `'${folderId}' in parents and ${query}`;
  }

  const url = `https://www.googleapis.com/drive/v3/files?q=${encodeURIComponent(query)}&fields=files(id,name,size,createdTime,webViewLink,parents)&pageSize=100`;
  const res = await fetch(url, {
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || 'خطا در خواندن فایل‌های گوگل درایو');
  }

  const data = await res.json();
  return (data.files || []).map((f: any) => {
    // Parse resolution and video ID from name if present
    const matchId = f.name.match(/\[([a-zA-Z0-9_-]{11})\]/);
    const matchHeight = f.name.match(/\[(\d+)p\]/);

    return {
      id: f.id,
      name: f.name,
      videoId: matchId ? matchId[1] : null,
      height: matchHeight ? parseInt(matchHeight[1], 10) : 1080,
      size: Number(f.size || 0),
      createdTime: f.createdTime || new Date().toISOString(),
      driveUrl: f.webViewLink || `https://drive.google.com/file/d/${f.id}/view`
    };
  });
}

// Create or find a designated folder in Drive
export async function getOrCreateVaultFolder(accessToken: string, folderName = 'YouTube_Vault_AutoSync'): Promise<string> {
  // Check if folder already exists
  const checkUrl = `https://www.googleapis.com/drive/v3/files?q=${encodeURIComponent(
    `name = '${folderName}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false`
  )}&fields=files(id,name)`;

  const checkRes = await fetch(checkUrl, {
    headers: { Authorization: `Bearer ${accessToken}` }
  });

  if (checkRes.ok) {
    const data = await checkRes.json();
    if (data.files && data.files.length > 0) {
      return data.files[0].id;
    }
  }

  // Create folder
  const createRes = await fetch('https://www.googleapis.com/drive/v3/files', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      name: folderName,
      mimeType: 'application/vnd.google-apps.folder'
    })
  });

  if (!createRes.ok) {
    throw new Error('خطا در ایجاد پوشه در گوگل درایو');
  }

  const newFolder = await createRes.json();
  return newFolder.id;
}
