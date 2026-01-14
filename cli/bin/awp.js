#!/usr/bin/env node

import { program } from 'commander';
import chalk from 'chalk';

import { initCommand } from '../src/commands/init.js';
import { analyzeCommand } from '../src/commands/analyze.js';
import { generateCommand } from '../src/commands/generate.js';
import { exportCommand } from '../src/commands/export.js';

program
  .name('awp')
  .description('Auto White Paper - Generate academic papers from GitHub repositories')
  .version('0.1.0');

program
  .command('init [project-name]')
  .description('Initialize a new paper project')
  .option('-t, --template <template>', 'Paper template (ieee, ieej, generic)', 'ieee')
  .option('-l, --language <lang>', 'Paper language (en, ja)', 'en')
  .option('-g, --github <url>', 'GitHub repository URL')
  .action(initCommand);

program
  .command('analyze <github-url>')
  .description('Analyze a GitHub repository')
  .option('-o, --output <dir>', 'Output directory', './output')
  .option('-d, --depth <depth>', 'Analysis depth (basic, full)', 'full')
  .action(analyzeCommand);

program
  .command('generate')
  .description('Generate paper content')
  .option('-c, --chapters <chapters>', 'Chapters to generate (e.g., "1,2,3" or "all")', 'all')
  .option('--resume', 'Resume from last checkpoint')
  .option('--review', 'Enable interactive review')
  .option('--dry-run', 'Show what would be generated')
  .action(generateCommand);

program
  .command('export')
  .description('Export to PDF/LaTeX')
  .option('-f, --format <format>', 'Output format (pdf, latex, markdown)', 'pdf')
  .option('-o, --output <path>', 'Output file path')
  .action(exportCommand);

program.parse();
