# Financial Advisor AI - CI/CD Pipeline Documentation

## Overview

This project includes a comprehensive CI/CD pipeline with Docker containerization, following industry best practices for deployment to fresh production environments.

## Architecture

### Services
- **Backend**: FastAPI application with PostgreSQL and Redis
- **Frontend**: React application served by Nginx
- **Database**: PostgreSQL with pgvector extension
- **Cache**: Redis for session management and caching
- **Reverse Proxy**: Nginx for load balancing and SSL termination

### Docker Images
- `backend`: Python 3.11-slim with FastAPI
- `frontend`: Node.js 18 with React, served by Nginx
- `postgres`: PostgreSQL 15 with pgvector
- `redis`: Redis 7 for caching
- `nginx`: Nginx Alpine for reverse proxy

## Quick Start

### Development Environment

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/advisor-ai.git
   cd advisor-ai
   ```

2. **Run the development setup script**
   ```bash
   chmod +x scripts/setup-dev.sh
   ./scripts/setup-dev.sh
   ```

3. **Start the application**
   ```bash
   # Terminal 1 - Backend
   ./start-backend.sh
   
   # Terminal 2 - Frontend
   ./start-frontend.sh
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Production Deployment

1. **Prepare your server**
   ```bash
   # On your production server
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   sudo usermod -aG docker $USER
   ```

2. **Run the deployment script**
   ```bash
   chmod +x scripts/deploy.sh
   ./scripts/deploy.sh
   ```

3. **Configure environment variables**
   ```bash
   # Copy and edit production environment
   cp env.production.example backend/.env.production
   nano backend/.env.production
   ```

4. **Restart services**
   ```bash
   sudo systemctl restart advisor-ai
   ```

## Docker Commands

### Development
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild and restart
docker-compose up -d --build
```

### Production
```bash
# Start production services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop services
docker-compose -f docker-compose.prod.yml down

# Update services
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

## CI/CD Pipeline

### GitHub Actions Workflow

The pipeline includes:

1. **Code Quality Checks**
   - Python: flake8, black, isort
   - JavaScript: ESLint, TypeScript checks
   - Test coverage reporting

2. **Security Scanning**
   - Trivy vulnerability scanner
   - Dependency vulnerability checks

3. **Build and Test**
   - Multi-stage Docker builds
   - Integration tests
   - Health checks

4. **Deployment**
   - Automated deployment to production
   - Rollback capabilities
   - Slack notifications

### Pipeline Triggers
- **Push to main**: Full CI/CD pipeline with deployment
- **Push to develop**: CI pipeline with testing only
- **Pull requests**: CI pipeline with testing and security scans

## Environment Configuration

### Development
- Uses `docker-compose.yml`
- Hot reloading enabled
- Debug logging
- Local database and Redis

### Production
- Uses `docker-compose.prod.yml`
- Optimized builds
- Health checks
- Logging and monitoring
- SSL/TLS termination
- Rate limiting

## Security Features

### Container Security
- Non-root users in containers
- Minimal base images
- Security scanning in CI/CD
- Regular dependency updates

### Application Security
- JWT authentication
- CORS configuration
- Rate limiting
- Input validation
- SQL injection prevention

### Infrastructure Security
- Firewall configuration (UFW)
- Fail2ban for intrusion prevention
- SSL/TLS encryption
- Regular security updates

## Monitoring and Logging

### Health Checks
- Application health endpoints
- Database connectivity checks
- Redis connectivity checks
- Container health monitoring

### Logging
- Structured logging with JSON format
- Log rotation and retention
- Centralized log collection
- Error tracking with Sentry

### Backup
- Automated daily backups
- 30-day retention policy
- Database and file backups
- Restore procedures

## Troubleshooting

### Common Issues

1. **Services not starting**
   ```bash
   # Check logs
   docker-compose logs -f
   
   # Check service status
   docker-compose ps
   ```

2. **Database connection issues**
   ```bash
   # Check database logs
   docker-compose logs postgres
   
   # Test connection
   docker-compose exec postgres psql -U advisor_user -d advisor_ai
   ```

3. **Frontend build issues**
   ```bash
   # Rebuild frontend
   docker-compose build frontend
   docker-compose up -d frontend
   ```

### Performance Optimization

1. **Database Optimization**
   - Index optimization
   - Query performance monitoring
   - Connection pooling

2. **Caching Strategy**
   - Redis for session storage
   - Application-level caching
   - CDN for static assets

3. **Container Optimization**
   - Multi-stage builds
   - Layer caching
   - Resource limits

## Maintenance

### Regular Tasks
- Update dependencies monthly
- Review security scans weekly
- Monitor disk space and logs
- Test backup restoration quarterly

### Scaling
- Horizontal scaling with load balancers
- Database read replicas
- Redis clustering
- Container orchestration (Kubernetes)

## Support

For issues and questions:
1. Check the logs first
2. Review this documentation
3. Create an issue in the repository
4. Contact the development team

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests locally
5. Submit a pull request

The CI/CD pipeline will automatically test your changes and provide feedback.