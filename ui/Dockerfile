FROM node:20.20.2-alpine

# Create non-root user
RUN addgroup -g 1000 appuser && adduser -u 1000 -G appuser -s /bin/sh -D appuser

WORKDIR /usr/src/app

# Install dependencies as root (needs write to node_modules)
COPY package.json package-lock.json* ./
RUN npm ci --ignore-scripts && npm cache clean --force

# Copy application code
COPY . .

# Own the app directory
RUN chown -R appuser:appuser /usr/src/app

USER appuser
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

CMD ["npm", "run", "dev", "--", "--port", "3000", "--hostname", "0.0.0.0"]
