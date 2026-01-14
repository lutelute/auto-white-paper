import chalk from 'chalk';
import fs from 'fs-extra';
import path from 'path';
import yaml from 'yaml';
import inquirer from 'inquirer';

export async function initCommand(projectName = 'paper', options) {
  console.log(chalk.bold.green('Initializing Auto White Paper project...'));
  console.log();

  // Interactive prompts if not provided
  let githubUrl = options.github;
  let template = options.template;
  let language = options.language;

  if (!githubUrl) {
    const answers = await inquirer.prompt([
      {
        type: 'input',
        name: 'githubUrl',
        message: 'GitHub repository URL:',
        validate: (input) => {
          if (!input) return 'Please enter a GitHub URL';
          if (!input.includes('github.com')) return 'Please enter a valid GitHub URL';
          return true;
        },
      },
      {
        type: 'list',
        name: 'template',
        message: 'Paper template:',
        choices: [
          { name: 'IEEE (International)', value: 'ieee' },
          { name: 'IEEJ (Japanese)', value: 'ieej' },
          { name: 'Generic', value: 'generic' },
        ],
        default: template,
      },
      {
        type: 'list',
        name: 'language',
        message: 'Paper language:',
        choices: [
          { name: 'English', value: 'en' },
          { name: 'Japanese (日本語)', value: 'ja' },
        ],
        default: language,
      },
    ]);

    githubUrl = answers.githubUrl;
    template = answers.template;
    language = answers.language;
  }

  // Create directory structure
  const dirs = [
    'output',
    'output/figures',
    '.awp',
    '.awp/cache',
  ];

  for (const dir of dirs) {
    await fs.ensureDir(dir);
    console.log(chalk.gray(`  Created: ${dir}/`));
  }

  // Create config file
  const config = {
    project: {
      name: projectName,
      output_dir: './output',
    },
    repository: {
      url: githubUrl,
      branch: 'main',
      clone_dir: './.awp/repo',
    },
    paper: {
      template: template,
      language: language,
      title: projectName,
      authors: [],
    },
    llm: {
      provider: 'claude',
      model: 'claude-sonnet-4-20250514',
      max_tokens: 4096,
      temperature: 0.7,
      literature_provider: 'genspark',
    },
    output: {
      formats: ['markdown', 'latex', 'pdf'],
    },
    review: {
      enabled: true,
      checkpoints: [1, 3, 5],
    },
  };

  const configPath = 'awp.config.yaml';
  await fs.writeFile(configPath, yaml.stringify(config));
  console.log(chalk.green(`  Created: ${configPath}`));

  // Create .env.example if not exists
  const envExample = `# Auto White Paper - Environment Variables

# Claude API (Anthropic) - Required
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Genspark API (for literature research)
GENSPARK_API_KEY=your_genspark_api_key_here

# GitHub Token (optional, for private repos)
GITHUB_TOKEN=your_github_token_here
`;

  if (!await fs.pathExists('.env')) {
    await fs.writeFile('.env.example', envExample);
    console.log(chalk.green(`  Created: .env.example`));
  }

  console.log();
  console.log(chalk.bold.green('✓ Project initialized successfully!'));
  console.log();
  console.log(chalk.bold('Next steps:'));
  console.log(chalk.gray('  1. Copy .env.example to .env and add your API keys'));
  console.log(chalk.gray('  2. Edit awp.config.yaml to customize settings'));
  console.log(chalk.gray('  3. Run: awp generate'));
  console.log();
}
