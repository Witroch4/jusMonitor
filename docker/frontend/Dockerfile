FROM node:24.14.0-alpine

# Install pnpm
RUN corepack enable && corepack prepare pnpm@10.30.3 --activate

# Set working directory
WORKDIR /app

# Install dependencies first (for better caching)
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# Copy application code
COPY . .

# Expose port
EXPOSE 3001

# Default command
CMD ["pnpm", "run", "dev"]
