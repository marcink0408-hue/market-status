import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import fs from 'fs';
import path from 'path';

const OUTPUT_DIR = path.resolve(__dirname, '..', 'output');

export default defineConfig({
  plugins: [react()],
  root: '.',
  publicDir: 'public',
  base: '/market-status/',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  server: {
    middleware: [
      (req, res, next) => {
        if (req.url.startsWith('/output/')) {
          const fileName = req.url.replace('/output/', '');
          const filePath = path.join(OUTPUT_DIR, fileName);
          if (fs.existsSync(filePath)) {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(fs.readFileSync(filePath));
            return;
          }
          res.writeHead(404, { 'Content-Type': 'text/plain' });
          res.end('Not found');
          return;
        }
        next();
      },
    ],
  },
});