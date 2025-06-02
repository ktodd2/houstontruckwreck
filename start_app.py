#!/usr/bin/env python3
"""
Simple startup script for Houston Traffic Monitor
"""

import sys
import os

def main():
    print("🚛 Houston Traffic Monitor - Starting...")
    print("=" * 50)
    
    try:
        # Import and start the app
        from app import app
        print("✅ App imported successfully")
        print("🌐 Starting web server...")
        print("📍 URL: http://localhost:5000")
        print("👤 Default login: admin / admin123")
        print("=" * 50)
        
        # Start the Flask app
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
        
    except KeyboardInterrupt:
        print("\n👋 Houston Traffic Monitor stopped by user")
    except Exception as e:
        print(f"❌ Error starting app: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
