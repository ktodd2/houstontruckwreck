# Deploying Houston Traffic Monitor on Render

This guide provides step-by-step instructions for deploying the Houston Traffic Monitor application on Render.

## Prerequisites

- A [Render](https://render.com) account
- Your GitHub repository with the Houston Traffic Monitor code
- Gmail account with App Password for email alerts

## Deployment Steps

### 1. Fork or Clone the Repository

Ensure you have the latest version of the Houston Traffic Monitor code in your GitHub repository.

### 2. Connect to Render

1. Log in to your Render account
2. Click on "New" and select "Blueprint" from the dropdown menu
3. Connect your GitHub account if you haven't already
4. Select the repository containing the Houston Traffic Monitor code
5. Render will automatically detect the `render.yaml` file and configure your service

### 3. Configure Environment Variables

The `render.yaml` file includes most of the necessary configuration, but you'll need to set these sensitive environment variables:

- `EMAIL_USERNAME`: Your Gmail address
- `EMAIL_PASSWORD`: Your Gmail app password
- `EMAIL_FROM`: Your from email address (optional, defaults to EMAIL_USERNAME)
- `ADMIN_PASSWORD`: Secure password for admin login

### 4. Deploy the Service

1. Click "Apply" to create the service
2. Render will automatically build and deploy your application
3. The build process may take a few minutes

### 5. Access Your Application

Once deployment is complete:

1. Click on the service name to view details
2. You'll find the URL for your application (e.g., `https://houston-traffic-monitor.onrender.com`)
3. Access the admin panel by navigating to this URL
4. Log in with:
   - Username: `admin` (or your configured ADMIN_USERNAME)
   - Password: Your configured ADMIN_PASSWORD

## Persistent Storage

The application is configured to use Render's disk storage for the SQLite database:

- The database will be stored at `/data/database.db`
- This ensures your data persists across deployments and restarts

## Monitoring and Logs

1. In the Render dashboard, click on your service
2. Select the "Logs" tab to view application logs
3. You can monitor:
   - Scraping activity
   - Email alerts
   - Error messages

## Troubleshooting

### Application Not Starting

- Check the logs for error messages
- Verify that all required environment variables are set
- Ensure the `gunicorn` package is in `requirements.txt`

### Database Errors ("unable to open database file")

If you encounter an error like "unable to open database file", it may be due to permission issues with the database directory. The application has been configured to:

1. Create the `/data` directory if it doesn't exist
2. Set appropriate permissions (777) on the directory
3. Ensure the database path exists before attempting to connect

These fixes should resolve most database permission issues on Render. If you still encounter problems:

- Check the Render logs for any permission-related errors
- Verify that the disk is properly mounted at `/data`
- Try redeploying the application

### Email Alerts Not Sending

- Verify your Gmail App Password is correct
- Check that 2-Factor Authentication is enabled on your Gmail account
- Ensure EMAIL_USERNAME and EMAIL_PASSWORD are set correctly

### Database Issues

- Check if the application has write permissions to the `/data` directory
- Verify the database is being created at `/data/database.db`

## Updating Your Application

When you push changes to your GitHub repository:

1. Render will automatically detect the changes
2. A new build will be triggered
3. Once the build completes, your application will be updated

## Additional Resources

- [Render Documentation](https://render.com/docs)
- [Gunicorn Documentation](https://docs.gunicorn.org/en/stable/)
- [Flask Deployment Guide](https://flask.palletsprojects.com/en/2.3.x/deploying/)
