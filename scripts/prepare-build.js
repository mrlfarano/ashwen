/**
 * Pre-build preparation script
 * 
 * Runs before electron-builder to ensure all necessary files and configurations
 * are in place for a successful build.
 */

const fs = require('fs');
const path = require('path');

exports.default = async function prepareBuild(context) {
  console.log('Preparing build...');
  
  const rootDir = path.resolve(__dirname, '..');
  
  // Ensure resources directory exists
  const resourcesDir = path.join(rootDir, 'resources');
  if (!fs.existsSync(resourcesDir)) {
    fs.mkdirSync(resourcesDir, { recursive: true });
  }
  
  // Create placeholder icons if they don't exist
  const iconFiles = [
    { name: 'icon.png', required: true },
    { name: 'icon.ico', required: false },
    { name: 'icon.icns', required: false }
  ];
  
  for (const iconFile of iconFiles) {
    const iconPath = path.join(resourcesDir, iconFile.name);
    if (!fs.existsSync(iconPath)) {
      if (iconFile.required) {
        console.warn(`Warning: Missing required icon file: ${iconFile.name}`);
      } else {
        console.log(`Note: Optional icon file not found: ${iconFile.name}`);
      }
    }
  }
  
  // Create placeholder NSIS include files if they don't exist
  const nsisFiles = ['installer.nsh', 'custom-install.nsi'];
  for (const nsisFile of nsisFiles) {
    const nsisPath = path.join(resourcesDir, nsisFile);
    if (!fs.existsSync(nsisPath)) {
      // Create empty placeholder
      fs.writeFileSync(nsisPath, `; ${nsisFile} placeholder for Ashwen installer\n`);
      console.log(`Created placeholder: ${nsisFile}`);
    }
  }
  
  // Verify frontend build exists
  const frontendBuildPath = path.join(rootDir, 'frontend', 'build');
  if (!fs.existsSync(frontendBuildPath)) {
    console.error('Error: Frontend build not found. Run "npm run build:frontend" first.');
    throw new Error('Frontend build not found');
  }
  
  const indexHtmlPath = path.join(frontendBuildPath, 'index.html');
  if (!fs.existsSync(indexHtmlPath)) {
    console.error('Error: Frontend index.html not found. Frontend build may be incomplete.');
    throw new Error('Frontend build incomplete');
  }
  
  // Verify backend build exists
  const backendDistPath = path.join(rootDir, 'dist', 'backend');
  if (!fs.existsSync(backendDistPath)) {
    console.error('Error: Backend build not found. Run "npm run build:backend" first.');
    throw new Error('Backend build not found');
  }
  
  const backendExe = process.platform === 'win32' 
    ? path.join(backendDistPath, 'ashwen-backend.exe')
    : path.join(backendDistPath, 'ashwen-backend');
  
  if (!fs.existsSync(backendExe)) {
    console.error(`Error: Backend executable not found: ${backendExe}`);
    throw new Error('Backend executable not found');
  }
  
  // Create LICENSE file if it doesn't exist
  const licensePath = path.join(rootDir, 'LICENSE');
  if (!fs.existsSync(licensePath)) {
    fs.writeFileSync(licensePath, `Ashwen Desktop Application
Copyright © ${new Date().getFullYear()} Ashwen

This software is provided as-is. See the project repository for license details.
`);
    console.log('Created placeholder LICENSE file');
  }
  
  console.log('Build preparation complete!');
};
