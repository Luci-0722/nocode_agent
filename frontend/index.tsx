#!/usr/bin/env node
import React from 'react';
import { render } from 'ink';
import App from './App.js';

const args = process.argv.slice(2);
const resume = args.includes('--resume');
const modelIndex = args.indexOf('--model');
const model = modelIndex >= 0 && modelIndex + 1 < args.length ? args[modelIndex + 1] : undefined;

render(<App resume={resume} model={model} />);
