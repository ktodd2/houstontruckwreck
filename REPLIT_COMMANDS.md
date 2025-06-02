# 🚛 Houston Traffic Monitor - Replit Commands

## ✅ **Correct Run Commands for Replit**

### **Automatic (Recommended)**
- **Click the "Run" button** (▶️) at the top of Replit
- The `.replit` file is configured to run automatically

### **Manual Commands (if needed)**
If the Run button doesn't work, use these commands in the **Shell tab**:

```bash
# Install dependencies
pip3 install -r requirements.txt

# Run the application
python3 main.py
```

## 🔧 **Important Notes**

### **Python Commands in Replit:**
- ✅ Use `python3` (NOT `python`)
- ✅ Use `pip3` (NOT `pip`)
- ✅ Replit uses Python 3.10 by default

### **Common Issues & Solutions:**

**❌ Error: `bash: python: command not found`**
- **Solution**: Use `python3` instead of `python`

**❌ Error: `bash: pip: command not found`**
- **Solution**: Use `pip3` instead of `pip`

**❌ Error: `ModuleNotFoundError`**
- **Solution**: Run `pip3 install -r requirements.txt` first

## 🚀 **Step-by-Step Replit Setup**

### **1. Import from GitHub**
- Go to Replit.com
- Click "Create Repl"
- Select "Import from GitHub"
- Enter your repository URL

### **2. Configure Secrets**
Click the **Secrets tab** (🔒) and add:
- `EMAIL_USERNAME` = `houstontruckwreck@gmail.com`
- `EMAIL_PASSWORD` = `your_gmail_app_password`
- `EMAIL_FROM` = `houstontruckwreck@gmail.com`
- `SCRAPE_INTERVAL` = `60`
- `MAX_ALERTS_PER_HOUR` = `20`
- `INCLUDE_STALLS` = `true`
- `ADMIN_USERNAME` = `admin`
- `ADMIN_PASSWORD` = `admin123`
- `SECRET_KEY` = `houston_traffic_monitor_secret_key_2025`

### **3. Run the Application**
- **Click the "Run" button** (▶️)
- **OR** use Shell command: `python3 main.py`

### **4. Access Your Dashboard**
- **URL**: Shown in console output
- **Format**: `https://your-repl-name.your-username.repl.co`
- **Login**: admin / admin123

## 🐛 **Troubleshooting**

### **If Run Button Doesn't Work:**
1. **Open Shell tab**
2. **Run**: `pip3 install -r requirements.txt`
3. **Run**: `python3 main.py`
4. **Check console** for any error messages

### **If Dependencies Fail:**
1. **Check internet connection**
2. **Try**: `pip3 install --upgrade pip`
3. **Then**: `pip3 install -r requirements.txt`

### **If App Won't Start:**
1. **Check Secrets** are all configured
2. **Look for error messages** in console
3. **Try restarting** the repl
4. **Check file permissions** (usually automatic)

## ✅ **Success Indicators**

When working correctly, you should see:
```
🚛 Houston Traffic Monitor Starting on Replit...
📊 Dashboard will be available at: https://your-repl.your-username.repl.co
👤 Default admin login: admin / admin123
⏱️  Scraping interval: 60 seconds
📧 Email configured: True
🔧 Configure your email settings in the Secrets tab!
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://10.0.0.1:5000
```

## 🎯 **Quick Test**

1. **Access the URL** shown in console
2. **Login** with admin/admin123
3. **Go to Subscribers** page
4. **Send test email** to verify email works
5. **Check Dashboard** for system status

---

**Your Houston Traffic Monitor should now be running successfully on Replit! 🚛📧**
