import chalk from 'chalk';
import ora from 'ora';
import { execa } from 'execa';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export async function analyzeCommand(githubUrl, options) {
  console.log(chalk.bold(`Analyzing repository: ${githubUrl}`));
  console.log();

  const spinner = ora('Cloning and analyzing repository...').start();

  try {
    // Call Python script
    const pythonScript = path.resolve(__dirname, '../../../src/main.py');

    const result = await execa('python', [
      pythonScript,
      'analyze',
      githubUrl,
      '--output', options.output,
    ], {
      stdio: 'pipe',
    });

    spinner.stop();
    console.log(result.stdout);

  } catch (error) {
    spinner.fail(chalk.red('Analysis failed'));
    console.error(chalk.red(error.message));

    if (error.stderr) {
      console.error(chalk.gray(error.stderr));
    }

    process.exit(1);
  }
}
