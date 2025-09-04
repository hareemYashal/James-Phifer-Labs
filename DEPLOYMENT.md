# Deployment Guide

This guide will help you deploy the Comprehensive PDF Extraction System with intelligent field mapping and sample comment support to various platforms.

## Local Deployment

### Prerequisites
- Python 3.8 or higher
- pip package manager
- Google Gemini 2.5 Flash API key

### Steps
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create `.env` file with your API key
4. Run the application

## Docker Deployment

### Build Docker Image
```bash
docker build -t pdf-extraction-system .
```

### Run with Docker
```bash
docker run -p 8000:8000 -e GEMINI_API_KEY=your_api_key pdf-extraction-system
```

### Docker Compose
```yaml
version: '3.8'
services:
  pdf-extraction-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    volumes:
      - ./uploads:/app/uploads
```

## Cloud Deployment

### Heroku
1. Create a new Heroku app
2. Set environment variables in Heroku dashboard
3. Deploy using Heroku CLI or GitHub integration

### AWS
1. Use AWS Elastic Beanstalk
2. Configure environment variables
3. Deploy via EB CLI or AWS Console

### Google Cloud Platform
1. Use Cloud Run or App Engine
2. Set environment variables
3. Deploy using gcloud CLI

## Environment Variables

Required environment variables:
- `GEMINI_API_KEY`: Your Google Gemini API key

## Security Considerations

1. **Never commit API keys** to version control
2. **Use environment variables** for sensitive data
3. **Enable HTTPS** in production
4. **Set up proper authentication** if needed
5. **Monitor API usage** and set rate limits

## Monitoring and Logging

- Set up application monitoring
- Configure error logging
- Monitor API response times
- Track usage metrics

## Troubleshooting

### Common Issues
1. **API Key not found**: Ensure `.env` file is properly configured
2. **Port already in use**: Change port number in `api.py`
3. **Memory issues**: Increase memory allocation for large PDFs
4. **Timeout errors**: Increase timeout settings for long-running extractions

### Support
For deployment issues, check:
1. Platform-specific documentation
2. Error logs and console output
3. Environment variable configuration
4. Network connectivity and firewall settings
