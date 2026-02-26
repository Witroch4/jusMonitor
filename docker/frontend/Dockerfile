FROM node:20-alpine

# Set working directory
WORKDIR /app

# Install dependencies first (for better caching)
COPY package.json package-lock.json* ./
RUN npm ci

# Copy application code
COPY . .

# Expose port
EXPOSE 3000

# Default command
CMD ["npm", "run", "dev"]
