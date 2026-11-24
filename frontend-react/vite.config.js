import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import fs from 'fs';
import path from 'path';

const OUTPUT_DIR = path.resolve(__dirname, '..', 'output');

const outputJsonPlugin = {
  name: 'serve-market-output',
  configureServer(server) {
    server.middlewares.use((req, res, next) => {
      const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
      const prefix = ['/market-status/output/', '/output/'].find((item) => pathname.startsWith(item));
      if (!prefix) {
        next();
        return;
      }
      const fileName = pathname.slice(prefix.length);
      const filePath = path.resolve(OUTPUT_DIR, fileName);
      if (!filePath.startsWith(OUTPUT_DIR + path.sep)) {
        res.writeHead(403, { 'Content-Type': 'text/plain' });
        res.end('Forbidden');
        return;
      }
      if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
        res.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
        res.end(fs.readFileSync(filePath));
        return;
      }
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('Not found');
    });
  },
};

export default defineConfig({
  plugins: [react(), outputJsonPlugin],
  root: '.',
  publicDir: 'public',
  base: '/market-status/',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
});