-- Database initialization script for Financial Advisor AI Assistant
-- This script sets up the PostgreSQL database with pgvector extension

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Create database if it doesn't exist (this will be handled by Docker)
-- CREATE DATABASE advisor_ai;

-- Grant permissions to the application user
-- GRANT ALL PRIVILEGES ON DATABASE advisor_ai TO advisor_user;

-- Note: All tables will be created by SQLAlchemy ORM models
-- This file is kept for reference and any additional database setup