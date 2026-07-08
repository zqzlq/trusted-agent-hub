#!/usr/bin/env node

import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import { loadPackages, loadVersionForPackage } from './mock-loader';
import { formatPackageCard, formatPackageDetail } from './format';
import {
  PACKAGE_TYPE_LABELS,
  CLIENT_LABELS,
} from '../../../packages/schema/constants';
import type { PackageType, Client } from '../../../packages/schema/constants';

// ── Program setup ───────────────────────────────────────────────────────

const program = new Command();

program
  .name('trusted-agent-hub')
  .description(
    chalk.bold('TrustedAgentHub CLI — AI agent capability package registry'),
  )
  .version('0.1.0');

// ── search ──────────────────────────────────────────────────────────────

program
  .command('search <keyword>')
  .description('Search packages by keyword (matches name, description, and keywords)')
  .option(
    '-t, --type <type>',
    'Filter by package type: skill, mcp_server, plugin, subagent, command, prompt',
  )
  .option(
    '-c, --client <client>',
    'Filter by client compatibility (e.g. claude-code, cursor, vscode)',
  )
  .action(
    (
      keyword: string,
      options: { type?: string; client?: string },
    ) => {
      const packages = loadPackages();
      const kw = keyword.toLowerCase().trim();

      // Keyword matching on name, description, and keyword tags
      let results = packages.filter((pkg) => {
        if (pkg.name.toLowerCase().includes(kw)) return true;
        if (pkg.description.toLowerCase().includes(kw)) return true;
        if (pkg.keywords.some((k) => k.toLowerCase().includes(kw))) return true;
        return false;
      });

      // Type filter
      if (options.type) {
        const before = results.length;
        results = results.filter((pkg) => pkg.type === options.type);
      }

      // Client compatibility filter
      if (options.client) {
        results = results.filter((pkg) => {
          const version = loadVersionForPackage(pkg);
          if (!version || !version.compatibility) return false;
          return version.compatibility.includes(options.client!);
        });
      }

      // Output
      console.log('');
      if (results.length === 0) {
        const filters: string[] = [];
        if (options.type) filters.push(`type="${options.type}"`);
        if (options.client) filters.push(`client="${options.client}"`);
        const suffix = filters.length > 0 ? ` with ${filters.join(', ')}` : '';
        console.log(
          chalk.yellow(`  No packages found for "${keyword}"${suffix}.`),
        );
      } else {
        const filterDesc: string[] = [];
        if (options.type) filterDesc.push(`type: ${options.type}`);
        if (options.client) filterDesc.push(`client: ${options.client}`);
        const suffix =
          filterDesc.length > 0 ? `  (filtered: ${filterDesc.join(', ')})` : '';

        console.log(
          chalk.bold(
            `  Found ${results.length} package(s) matching "${keyword}"${suffix}:`,
          ),
        );
        console.log('');
        results.forEach((pkg, idx) => {
          console.log(formatPackageCard(pkg));
          if (idx < results.length - 1) console.log('');
        });
      }
      console.log('');
    },
  );

// ── info ────────────────────────────────────────────────────────────────

program
  .command('info <name>')
  .description('Show detailed information about a package')
  .action((name: string) => {
    const packages = loadPackages();
    const pkg = packages.find((p) => p.name === name);

    if (!pkg) {
      console.log('');
      console.log(chalk.red(`  Package "${name}" not found.`));
      console.log(
        chalk.dim(`  Use "${chalk.cyan('trusted-agent-hub search <keyword>')}" to discover packages.`),
      );
      console.log('');
      return;
    }

    const version = loadVersionForPackage(pkg);
    console.log(formatPackageDetail(pkg, version));
  });

// ── install ─────────────────────────────────────────────────────────────

program
  .command('install <name>')
  .description('Install a package (stub — API integration pending)')
  .action(async (name: string) => {
    const packages = loadPackages();
    const pkg = packages.find((p) => p.name === name);

    if (!pkg) {
      console.log('');
      console.log(chalk.red(`  Package "${name}" not found.`));
      console.log(
        chalk.dim(`  Use "${chalk.cyan('trusted-agent-hub search <keyword>')}" to discover packages.`),
      );
      console.log('');
      return;
    }

    // Use ora for a brief loading animation to demonstrate the dependency
    const spinner = ora('Looking up package details…').start();
    const version = loadVersionForPackage(pkg);
    await new Promise((resolve) => setTimeout(resolve, 400));
    spinner.stop();

    console.log('');
    console.log(chalk.yellow.bold('  Coming soon — install logic pending API'));
    console.log('');
    console.log(
      `  ${chalk.dim('Package:')}  ${chalk.cyan(pkg.name)}  ${chalk.dim('v' + pkg.latest_version)}`,
    );
    console.log(
      `  ${chalk.dim('Type:')}     ${PACKAGE_TYPE_LABELS[pkg.type as PackageType] || pkg.type}`,
    );
    console.log(`  ${chalk.dim('Status:')}   ${pkg.status}`);
    console.log(`  ${chalk.dim('License:')}  ${pkg.license}`);

    if (version?.installation?.targets) {
      console.log(`  ${chalk.dim('Targets:')}`);
      for (const t of version.installation.targets) {
        console.log(`    ${chalk.dim('•')} ${t.client}: ${t.destination}`);
      }
    }

    if (version?.installation?.post_install_message) {
      console.log('');
      console.log(chalk.cyan(`  ℹ ${version.installation.post_install_message}`));
    }

    if (version?.installation?.command) {
      console.log(
        `  ${chalk.dim('Setup:')}    ${version.installation.command}`,
      );
    }

    if (pkg.homepage) {
      console.log(`  ${chalk.dim('Homepage:')} ${pkg.homepage}`);
    }

    console.log('');
    console.log(
      chalk.dim('  Install will be available once the backend API ships.'),
    );
    console.log('');
  });

// ── Parse ───────────────────────────────────────────────────────────────

program.parse();
