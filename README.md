# PR Bot

A bot for automating PR signups across multiple services.

## Developer Guide

### Project Structure 

### Key Components
1. **PRBot Class**: Main bot implementation
   - Browser management
   - Form filling
   - Site management
   - User info handling

2. **Sites Management**
   - Stored in sites.json
   - CRUD operations for sites
   - Site status tracking

3. **Form Handling**
   - Human-like typing
   - Field validation
   - Error handling
   - Success verification

### Adding New Sites
1. Use site management interface or edit sites.json
2. Required fields:
   ```json
   {
     "name": "Site Name",
     "url": "https://site-url.com",
     "type": "primary/secondary",
     "enabled": true/false
   }
   ```

### Error Handling
- Screenshots saved on errors
- Detailed logging
- Graceful failure handling

## User Guide

### Quick Start
1. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the bot:
   ```bash
   python pr.py
   ```

### Basic Usage
1. Enter user information (Option 1)
2. Start signup process (Option 2)
3. View/manage sites (Option 4)
4. Check logs (Option 5)

### Site Management
- View active sites
- Add new sites
- Enable/disable sites
- Update existing sites

### Tips
- Enter information carefully
- Check logs for errors
- Keep sites.json updated
- Use 'all' option for batch signup

### Support
For issues and feature requests, create an issue in the repository. 