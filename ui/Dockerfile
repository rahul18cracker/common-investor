FROM node:18-alpine
WORKDIR /usr/src/app
COPY package.json package-lock.json* ./
RUN npm install || true
COPY . .
EXPOSE 3000
CMD ["/bin/sh", "-c", "npm install && npm run dev -- --port 3000 --hostname 0.0.0.0"]