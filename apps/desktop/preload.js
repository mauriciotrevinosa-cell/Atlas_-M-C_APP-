/**
 * ARIA Terminal - Preload Script
 * 
 * Exposes safe IPC methods to renderer process
 */

const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods
contextBridge.exposeInMainWorld('electron', {
  // Window controls
  minimize: () => ipcRenderer.send('window-minimize'),
  maximize: () => ipcRenderer.send('window-maximize'),
  close: () => ipcRenderer.send('window-close'),

  // Settings
  getServerUrl: () => ipcRenderer.invoke('get-server-url'),
  saveSettings: (settings) => ipcRenderer.invoke('save-settings', settings),

  // Platform info
  platform: process.platform,
  version: process.versions.electron
});

console.log('ARIA Terminal preload script loaded');
