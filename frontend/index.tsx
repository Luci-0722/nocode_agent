#!/usr/bin/env node
import React from 'react';
import { render } from 'ink';
import App from './App.js';

// 解析命令行参数
const args = process.argv.slice(2);
const resume = args.includes('--resume');
const modelIndex = args.indexOf('--model');
const model = modelIndex >= 0 && modelIndex + 1 < args.length ? args[modelIndex + 1] : undefined;

// 启动应用
render(<App />);