# How to Create a Fresh Repository (No History)

If you want a clean repository with only your commits:

## Steps

1. **Create a new repository on GitHub**
   - Name: `homeassistant-dlink-smartplug`
   - Don't initialize with README

2. **Create a fresh local repository:**
   ```powershell
   # Navigate to a new directory
   cd ..
   mkdir homeassistant-dlink-smartplug-fresh
   cd homeassistant-dlink-smartplug-fresh
   
   # Copy your integration files
   # (copy custom_components folder, README.md, LICENSE, .gitignore)
   
   # Initialize fresh git
   git init
   git add .
   git commit -m "Initial commit: D-Link Smart Plug Home Assistant integration"
   git branch -M main
   git remote add origin https://github.com/Andrei-Iosifescu123/homeassistant-dlink-smartplug.git
   git push -u origin main --force
   ```

3. **Note:** This will overwrite the existing repository. Make sure you have backups.

## Alternative: Keep History but Add Attribution

You can keep the history but add a clear attribution section in your README crediting the original authors. This is actually the recommended approach for open source projects.


