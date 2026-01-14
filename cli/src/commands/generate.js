import chalk from 'chalk';
import ora from 'ora';
import inquirer from 'inquirer';
import { execa } from 'execa';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs-extra';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export async function generateCommand(options) {
  // Check for config file
  if (!await fs.pathExists('awp.config.yaml')) {
    console.log(chalk.red('Error: No awp.config.yaml found. Run "awp init" first.'));
    process.exit(1);
  }

  // Check for .env file
  if (!await fs.pathExists('.env')) {
    console.log(chalk.yellow('Warning: No .env file found. Make sure API keys are set.'));
  }

  console.log(chalk.bold('Generating paper...'));
  console.log();

  if (options.dryRun) {
    console.log(chalk.yellow('Dry run mode - showing what would be generated:'));
    const chapters = options.chapters === 'all'
      ? [1, 2, 3, 4, 5, 6, 7]
      : options.chapters.split(',').map(c => parseInt(c.trim()));

    const chapterNames = {
      1: 'Introduction',
      2: 'Existing Methods',
      3: 'Proposed Method',
      4: 'Implementation',
      5: 'Experiments',
      6: 'Discussion',
      7: 'Conclusion',
    };

    for (const ch of chapters) {
      console.log(chalk.gray(`  Chapter ${ch}: ${chapterNames[ch] || 'Unknown'}`));
    }
    return;
  }

  const spinner = ora('Starting paper generation...').start();

  try {
    // Call Python script
    const pythonScript = path.resolve(__dirname, '../../../src/main.py');

    const args = ['generate', '--chapters', options.chapters];

    if (options.resume) {
      args.push('--resume');
    }

    const subprocess = execa('python', [pythonScript, ...args], {
      stdio: options.review ? 'pipe' : 'inherit',
    });

    if (options.review) {
      subprocess.stdout.on('data', async (data) => {
        const output = data.toString();
        spinner.stop();
        process.stdout.write(output);

        // Check for review prompts
        if (output.includes('[REVIEW]')) {
          const { action } = await inquirer.prompt([{
            type: 'list',
            name: 'action',
            message: 'Review this chapter:',
            choices: [
              { name: 'Approve and continue', value: 'approve' },
              { name: 'Regenerate', value: 'regenerate' },
              { name: 'Skip', value: 'skip' },
              { name: 'Abort', value: 'abort' },
            ],
          }]);

          if (action === 'abort') {
            subprocess.kill();
            console.log(chalk.yellow('Generation aborted.'));
            process.exit(0);
          }

          subprocess.stdin.write(action + '\n');
          spinner.start('Continuing...');
        }
      });

      subprocess.stderr.on('data', (data) => {
        console.error(chalk.red(data.toString()));
      });
    }

    await subprocess;
    spinner.succeed(chalk.green('Paper generation completed!'));

    console.log();
    console.log(chalk.bold('Output files:'));
    console.log(chalk.gray('  ./output/paper.md'));
    console.log(chalk.gray('  ./output/paper.tex'));
    console.log(chalk.gray('  ./output/paper.pdf (if LaTeX compiled)'));

  } catch (error) {
    spinner.fail(chalk.red('Generation failed'));

    if (error.stderr) {
      console.error(chalk.gray(error.stderr));
    } else {
      console.error(chalk.red(error.message));
    }

    process.exit(1);
  }
}
