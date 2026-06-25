FROM node:20.19-slim

WORKDIR /app

COPY apps/frontend/package*.json ./
RUN npm ci

COPY apps/frontend ./

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
