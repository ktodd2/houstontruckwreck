# 🚛 Houston Traffic Monitor

A real-time traffic monitoring system that scrapes Houston TranStar for heavy truck incidents and hazmat spills, sending professional email alerts with custom branding.

![Houston Traffic Monitor](https://img.shields.io/badge/Status-Active-brightgreen)
![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Flask](https://img.shields.io/badge/Flask-2.0+-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Features

### 🚨 **Real-Time Monitoring**
- Monitors Houston TranStar every 60 seconds
- Smart filtering for heavy trucks, semis, 18-wheelers
- Detects hazmat spills and chemical incidents
- Configurable stall alert filtering

### 📧 **Professional Email Alerts**
- Custom logo integration in all emails
- HTML and plain text email templates
- Google Maps links for incident locations
- Color-coded priority system (🔴 High, 🟡 Medium, 🟢 Low)
- Automatic deduplication (one alert per incident)
- Rate limiting (max 20 alerts/hour)

### 👥 **Admin Dashboard**
- Web-based subscriber management
- Real-time system monitoring
- Manual scrape capability
- Email testing functionality
- Settings configuration with stall toggle

### 🔧 **Technical Features**
- SQLite database for persistence
- Background scheduling with APScheduler
- Responsive Bootstrap UI
- Secure admin authentication
- Input validation and error handling

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Gmail account with App Password

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/houston-traffic-monitor.git
   cd houston-traffic-monitor
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your email credentials
   ```

4. **Run the application**
   ```bash
   python start_app.py
   ```

5. **Access the admin panel**
   - URL: http://localhost:5000
   - Username: `admin`
   - Password: `admin123`

## ⚙️ Configuration

### Email Setup (Gmail)

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate App Password**:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate password for "Mail"
3. **Update .env file**:
   ```env
   EMAIL_USERNAME=your_email@gmail.com
   EMAIL_PASSWORD=your_16_character_app_password
   EMAIL_FROM=your_email@gmail.com
   ```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `EMAIL_USERNAME` | Gmail address | Required |
| `EMAIL_PASSWORD` | Gmail app password | Required |
| `EMAIL_FROM` | From email address | Same as username |
| `SCRAPE_INTERVAL` | Scraping interval (seconds) | 60 |
| `MAX_ALERTS_PER_HOUR` | Rate limit for alerts | 20 |
| `INCLUDE_STALLS` | Include stall alerts | true |
| `ADMIN_USERNAME` | Admin login username | admin |
| `ADMIN_PASSWORD` | Admin login password | admin123 |

## 📊 System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   TranStar      │    │   Houston        │    │   Email         │
│   Website       │───▶│   Traffic        │───▶│   Subscribers   │
│                 │    │   Monitor        │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │   Admin          │
                       │   Dashboard      │
                       │                  │
                       └──────────────────┘
```

### Components

- **Scraper**: Monitors Houston TranStar for incidents
- **Filter**: Smart filtering for relevant heavy truck incidents
- **Database**: SQLite storage for incidents, subscribers, alerts
- **Email Service**: Professional HTML email alerts
- **Web Interface**: Admin dashboard for management
- **Scheduler**: Background task automation

## 🎯 Alert Types

### Always Monitored
- ✅ Heavy truck accidents & crashes
- ✅ Hazmat spills & chemical leaks
- ✅ Rollover incidents
- ✅ Multi-vehicle accidents involving trucks

### Configurable (Stall Toggle)
- 🔄 Heavy truck stalls
- 🔄 Vehicle breakdowns
- 🔄 Disabled vehicles

## 📱 Usage

### Adding Subscribers
1. Login to admin panel
2. Navigate to "Subscribers"
3. Enter email address
4. Click "Add Subscriber"

### Testing Email System
1. Go to "Subscribers" page
2. Enter test email address
3. Click "Send Test Email"
4. Check inbox for test message

### Configuring Stall Alerts
1. Navigate to "Settings"
2. Find "Alert Filtering" section
3. Toggle "Enable/Disable Stall Alerts"
4. Changes take effect immediately

### Manual Scraping
1. Go to "Dashboard"
2. Click "Manual Scrape" button
3. System will check for new incidents
4. Alerts sent if new incidents found

## 🔒 Security

- **Password Hashing**: Secure admin authentication
- **Session Management**: Flask-Login integration
- **Input Validation**: Email format validation
- **Rate Limiting**: Prevents email spam
- **Environment Variables**: Sensitive data protection

## 📁 Project Structure

```
houston-traffic-monitor/
├── app.py                 # Main Flask application
├── config.py             # Configuration settings
├── models.py             # Database models
├── scraper.py            # TranStar scraping logic
├── email_service.py      # Email alert system
├── start_app.py          # Application launcher
├── requirements.txt      # Python dependencies
├── .env.example          # Environment template
├── .gitignore           # Git ignore rules
├── README.md            # Project documentation
└── templates/           # HTML templates
    ├── base.html        # Base template
    ├── login.html       # Admin login
    ├── dashboard.html   # Main dashboard
    ├── settings.html    # System settings
    └── subscribers.html # Subscriber management
```

## 🚀 Deployment

### Local Development
```bash
python start_app.py
```

### Production Deployment

**Render:**
1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Render will automatically detect the configuration from `render.yaml`
4. Set the following environment variables in the Render dashboard:
   - `EMAIL_USERNAME`: Your Gmail address
   - `EMAIL_PASSWORD`: Your Gmail app password
   - `EMAIL_FROM`: Your from email address (optional)
   - `ADMIN_PASSWORD`: Secure password for admin login
5. Deploy the service
6. Your application will be available at `https://your-service-name.onrender.com`

**Heroku:**
```bash
# Install Heroku CLI
heroku create your-app-name
heroku config:set EMAIL_USERNAME=your_email@gmail.com
heroku config:set EMAIL_PASSWORD=your_app_password
git push heroku main
```

**DigitalOcean/AWS:**
- Use gunicorn for production WSGI server
- Configure environment variables
- Set up reverse proxy (nginx)
- Enable HTTPS with SSL certificate

## 🐛 Troubleshooting

### Common Issues

**Email not sending:**
- Verify Gmail App Password is correct
- Check 2-Factor Authentication is enabled
- Ensure EMAIL_USERNAME and EMAIL_PASSWORD are set

**No incidents detected:**
- Check TranStar website accessibility
- Verify scraping interval in logs
- Try manual scrape from dashboard

**Database errors:**
- Ensure write permissions in project directory
- Check SQLite installation
- Verify database.db file creation

### Logs
System logs are displayed in the console. Look for:
- `✅ Alert sent successfully` - Email alerts sent
- `Running scheduled scrape...` - Scraper activity
- `No new incidents found` - Normal operation
- `❌ Failed to send alerts` - Email issues

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Houston TranStar for traffic data
- Flask community for excellent documentation
- Bootstrap for responsive UI components

## 📞 Support

For support, please open an issue on GitHub or contact the maintainer.

---

**Built with ❤️ for Houston traffic safety**
