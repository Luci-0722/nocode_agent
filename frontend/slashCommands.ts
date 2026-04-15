export interface SlashCommandDefinition {
  action: 'help' | 'clear' | 'session' | 'resume' | 'models' | 'permission' | 'cancel' | 'quit';
  name: string;
  description: string;
  argumentHint?: string;
  acceptsArgs?: boolean;
  aliases?: string[];
}

export const SLASH_COMMANDS: SlashCommandDefinition[] = [
  {
    action: 'help',
    name: 'help',
    description: '查看可用命令与快捷键',
  },
  {
    action: 'clear',
    name: 'clear',
    description: '清空当前会话内容',
  },
  {
    action: 'session',
    name: 'session',
    description: '刷新并显示当前会话状态',
    aliases: ['status'],
  },
  {
    action: 'resume',
    name: 'resume',
    description: '恢复历史会话',
    argumentHint: '[thread-id|关键词]',
    acceptsArgs: true,
  },
  {
    action: 'models',
    name: 'models',
    description: '列出或切换模型配置',
    argumentHint: '[model-name]',
    acceptsArgs: true,
  },
  {
    action: 'permission',
    name: 'permission',
    description: '设置工具审批模式',
    argumentHint: '[ask|all]',
    acceptsArgs: true,
    aliases: ['perm'],
  },
  {
    action: 'cancel',
    name: 'cancel',
    description: '中断当前生成或请求',
  },
  {
    action: 'quit',
    name: 'quit',
    description: '退出 NoCode',
    aliases: ['exit'],
  },
];

export function getSlashCommandSuggestions(query: string): SlashCommandDefinition[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    return [...SLASH_COMMANDS];
  }

  return [...SLASH_COMMANDS]
    .filter(
      (command) =>
        command.name.startsWith(normalized) ||
        command.aliases?.some((alias) => alias.startsWith(normalized)),
    )
    .sort((left, right) => {
      const leftNameMatch = left.name.startsWith(normalized) ? 0 : 1;
      const rightNameMatch = right.name.startsWith(normalized) ? 0 : 1;
      if (leftNameMatch !== rightNameMatch) {
        return leftNameMatch - rightNameMatch;
      }
      return left.name.localeCompare(right.name);
    });
}

export function buildSlashCommandHelpText(): string {
  return [
    'Slash commands:',
    ...SLASH_COMMANDS.map((command) => {
      const label = `/${command.name}${command.argumentHint ? ` ${command.argumentHint}` : ''}`;
      const aliases = command.aliases?.length
        ? ` (别名: ${command.aliases.map((alias) => `/${alias}`).join(', ')})`
        : '';
      return `  ${label}  ${command.description}${aliases}`;
    }),
    '',
    '输入 / 会自动弹出命令候选，可用 ↑/↓ 选择，Tab 补全，Enter 执行。',
  ].join('\n');
}
