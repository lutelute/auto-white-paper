import chalk from 'chalk';
import ora from 'ora';
import { execa } from 'execa';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs-extra';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export async function exportCommand(options) {
  // Check for paper.md
  if (!await fs.pathExists('./output/paper.md')) {
    console.log(chalk.red('Error: No paper.md found. Run "awp generate" first.'));
    process.exit(1);
  }

  console.log(chalk.bold(`Exporting to ${options.format}...`));

  const spinner = ora('Exporting...').start();

  try {
    const pythonScript = path.resolve(__dirname, '../../../src/main.py');

    const args = ['export', '--format', options.format];
    if (options.output) {
      args.push('--output', options.output);
    }

    const result = await execa('python', [pythonScript, ...args], {
      stdio: 'pipe',
    });

    spinner.stop();
    console.log(result.stdout);

  } catch (error) {
    spinner.fail(chalk.red('Export failed'));

    if (error.stderr) {
      console.error(chalk.gray(error.stderr));
    } else {
      console.error(chalk.red(error.message));
    }

    // If PDF compilation fails, suggest alternatives
    if (options.format === 'pdf') {
      console.log();
      console.log(chalk.yellow('Tip: If PDF compilation fails, try:'));
      console.log(chalk.gray('  1. Install LaTeX (e.g., texlive, mactex)'));
      console.log(chalk.gray('  2. Use: awp export --format latex'));
      console.log(chalk.gray('  3. Compile manually or use Overleaf'));
    }

    process.exit(1);
  }
}
