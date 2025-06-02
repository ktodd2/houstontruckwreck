# 🚛 Houston Traffic Monitor - Replit Deployment Guide

## 🚀 Setting Up Your Houston Traffic Monitor on Replit

### Step 1: Import from GitHub

1. **Go to Replit.com** and log in to your account
2. **Click "Create Repl"**
3. **Select "Import from GitHub"**
4. **Enter your repository URL**: `https://github.com/YOUR_USERNAME/houston-traffic-monitor`
5. **Click "Import from GitHub"**

### Step 2: Configure Environment Variables (Secrets)

Replit uses "Secrets" for environment variables. You need to configure these:

1. **Click the "Secrets" tab** (🔒 icon) in the left sidebar
2. **Add the following secrets**:

| Key | Value | Description |
|-----|-------|-------------|
| `EMAIL_USERNAME` | `your_email@gmail.com` | Your Gmail address |
| `EMAIL_PASSWORD` | `your_app_password` | Gmail App Password (16 characters) |
| `EMAIL_FROM` | `your_email@gmail.com` | From email address |
| `SCRAPE_INTERVAL` | `60` | Scraping interval in seconds |
| `MAX_ALERTS_PER_HOUR` | `20` | Maximum alerts per hour |
| `INCLUDE_STALLS` | `true` | Include stall alerts |
| `ADMIN_USERNAME` | `admin` | Admin login username |
| `ADMIN_PASSWORD` | `admin123` | Admin login password |
| `SECRET_KEY` | `houston_traffic_monitor_secret_key_2025` | Flask secret key |

### Step 3: Gmail App Password Setup

**Important**: You need a Gmail App Password for email functionality:

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Go to Google Account Settings**:
   - Security → 2-Step Verification → App passwords
3. **Generate App Password**:
   - Select "Mail" as the app
   - Copy the 16-character password
4. **Use this password** in the `EMAIL_PASSWORD` secret

### Step 4: Run Your Application

1. **Click the "Run" button** (▶️) at the top
2. **Wait for installation** - Replit will install dependencies automatically
3. **Your app will start** and show the URL in the console
4. **Click the URL** or use the web view to access your dashboard

### Step 5: Access Your Dashboard

- **URL Format**: `https://your-repl-name.your-username.repl.co`
- **Admin Login**: 
  - Username: `admin` (or your custom username)
  - Password: `admin123` (or your custom password)

## 🔧 Replit-Specific Features

### **Always-On (Replit Hacker Plan)**
- Enable "Always On" to keep your monitor running 24/7
- Without this, the repl will sleep after inactivity

### **Custom Domain (Optional)**
- Link a custom domain to your repl
- Makes it easier to access and share

### **Database Persistence**
- Your SQLite database will persist between runs
- Subscriber data and settings are saved automatically

## 📊 Monitoring Your System

### **Console Logs**
Check the console for system activity:
- `✅ Alert sent successfully` - Email alerts working
- `Running scheduled scrape...` - System is monitoring
- `No new incidents found` - Normal operation
- `❌ Failed to send alerts` - Check email configuration

### **Web Interface**
- **Dashboard**: Real-time system status
- **Subscribers**: Manage email list
- **Settings**: Configure stall alerts
- **Manual Scrape**: Test the system

## 🐛 Troubleshooting

### **Common Issues**

**1. Email Not Working:**
- Verify Gmail App Password is correct
- Check all email secrets are set
- Ensure 2FA is enabled on Gmail

**2. Repl Won't Start:**
- Check console for error messages
- Verify all required files are present
- Try refreshing the page

**3. Database Errors:**
- Replit should handle file permissions automatically
- Try restarting the repl if issues persist

**4. Scraping Not Working:**
- Check internet connectivity
- Verify TranStar website is accessible
- Look for error messages in console

### **Performance Tips**

**1. Keep It Running:**
- Use "Always On" feature for 24/7 monitoring
- Without it, repl sleeps after 1 hour of inactivity

**2. Monitor Resource Usage:**
- Replit has CPU and memory limits
- The app is designed to be lightweight

**3. Email Rate Limiting:**
- Default: 20 alerts per hour maximum
- Prevents spam and stays within limits

## 🔒 Security on Replit

### **Environment Variables**
- ✅ All sensitive data in Secrets tab
- ✅ No credentials in code
- ✅ Secrets are encrypted by Replit

### **Database Security**
- ✅ SQLite file is private to your repl
- ✅ Admin authentication required
- ✅ Input validation on all forms

### **Network Security**
- ✅ HTTPS enabled by default
- ✅ Secure session management
- ✅ Rate limiting implemented

## 🚀 Going Live

### **Share Your Monitor**
1. **Get your repl URL** from the web view
2. **Share with team members** or clients
3. **Add subscribers** through the admin interface
4. **Test email functionality** before going live

### **Production Checklist**
- [ ] All email secrets configured
- [ ] Gmail App Password working
- [ ] Test email sent successfully
- [ ] Subscribers added
- [ ] Stall alerts configured as desired
- [ ] Always On enabled (if available)
- [ ] Admin password changed from default

## 📱 Mobile Access

Your Houston Traffic Monitor works great on mobile devices:
- **Responsive design** adapts to phone screens
- **Touch-friendly** interface
- **Fast loading** on mobile networks

## 🎯 Next Steps

1. **Configure Email**: Set up Gmail App Password
2. **Add Subscribers**: Start with test emails
3. **Test System**: Send test emails and try manual scrape
4. **Monitor Activity**: Watch console logs for system health
5. **Enable Always On**: For 24/7 monitoring (Hacker plan)

## 📞 Support

If you encounter issues:
1. **Check console logs** for error messages
2. **Verify all secrets** are configured correctly
3. **Test email setup** with Gmail App Password
4. **Try restarting** the repl
5. **Check Replit status** page for platform issues

---

**Your Houston Traffic Monitor is now ready to run 24/7 on Replit! 🚛📧**
