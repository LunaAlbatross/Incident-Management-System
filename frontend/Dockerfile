FROM node:22-slim

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

# Use --host to allow external access (from docker host to container)
CMD ["npm", "run", "dev", "--", "--host"]
