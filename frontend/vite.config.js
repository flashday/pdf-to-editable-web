import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'
import fs from 'fs'

// 自定义插件：处理多入口路由
function multiPagePlugin() {
  return {
    name: 'multi-page-plugin',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        // 如果请求路径以 /workbench 开头，且不是静态资源请求，返回 workbench 的 index.html
        if (req.url && req.url.startsWith('/workbench')) {
          const urlPath = req.url.split('?')[0];
          // 只处理 HTML 页面请求，不处理静态资源
          if (!urlPath.includes('.') || urlPath.endsWith('.html')) {
            req.url = '/workbench/index.html';
          }
        }
        next();
      });
    }
  };
}

export default defineConfig({
  root: 'src',
  plugins: [
    multiPagePlugin(),
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
    // 处理 SPA 路由 - 将 /workbench 路由到 workbench/index.html
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
      },
      '/temp': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
        secure: false
      }
    }
  }
})
