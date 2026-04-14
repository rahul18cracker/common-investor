FROM node:20.20.2-alpine

WORKDIR /usr/src/app

# Install dependencies as root (needs write to node_modules)
COPY package.json package-lock.json* ./
RUN npm ci --ignore-scripts && npm cache clean --force

# Copy application code
COPY . .

# Own the app directory and switch to non-root user
# node:alpine ships with 'node' user (uid 1000) built-in
RUN chown -R node:node /usr/src/app

USER node
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

CMD ["npm", "run", "dev", "--", "--port", "3000", "--hostname", "0.0.0.0"]
