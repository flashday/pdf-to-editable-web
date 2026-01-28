import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
  root: 'src',
  plugins: [
    react({
      // 只对 workbench 目录下的文件启用 React 转换
      include: /workbench\/.*\.(tsx|ts|jsx|js)$/
    })
  ],
  build: {
    outDir: '../dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'src/index.html'),
        workbench: resolve(__dirname, 'src/workbench/index.html')
      }
    }
  },
  // 禁用依赖预构建缓存
  optimizeDeps: {
    force: true,
    include: ['react', 'react-dom', 'react-router-dom', 'zustand']
  },
  resolve: {
    alias: {
      '@workbench': resolve(__dirname, 'src/workbench')
    }
  },
  server: {
    port: 3000,
    host: '127.0.0.1',  // Force IPv4
    // 禁用浏览器缓存
    headers: {
      'Cache-Control': 'no-store'
    },
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5000',  // Use IPv4 explicitly
        changeOrigin: true,
        secure: false,
        ws: true,
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            console.log('proxy error', err);
          });
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            console.log('Sending Request to the Target:', req.method, req.url);
          });
          proxy.on('proxyRes', (proxyRes, req, _res) => {
            console.log('Received Response from the Target:', proxyRes.statusCode, req.url);
          });
        }
      }
    }
  }
})
