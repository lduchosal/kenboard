// @ts-check
// VS Code glue: sidebar tree of the current project's tasks, task detail
// (markdown), "Move to…", "Open in kenboard". All kenboard access goes through the REST API (ken #1127).

const crypto = require('node:crypto');
const vscode = require('vscode');
const { resolveConfig, configProblem } = require('./config');
const { KenApi, boardUrl } = require('./api');
const { TREE_STATUSES, ALL_STATUSES, groupByStatus, taskLabel } = require('./tree');
const { detailHtml } = require('./detail');

/** @typedef {import('./api').Task} Task */
/** @typedef {{ kind: 'status', status: string, tasks: Task[] } | { kind: 'task', task: Task } | { kind: 'message', text: string }} Node */

/** @implements {vscode.TreeDataProvider<Node>} */
class TaskTreeProvider {
  constructor() {
    /** @type {vscode.EventEmitter<Node | undefined>} */
    this.emitter = new vscode.EventEmitter();
    this.onDidChangeTreeData = this.emitter.event;
    /** @type {InstanceType<typeof KenApi> | null} */
    this.api = null;
    /** @type {import('./api').Project | null} */
    this.project = null;
    /** @type {Map<string, Task[]> | null} */
    this.groups = null;
    /** @type {string | null} */
    this.error = null;
  }

  async reload() {
    this.groups = null;
    this.error = null;
    const folder = vscode.workspace.workspaceFolders?.[0];
    if (!folder) {
      this.error = 'Ouvrir un dossier contenant ken.ini / .ken.';
    } else {
      const cfg = resolveConfig(folder.uri.fsPath);
      this.error = configProblem(cfg);
      if (!this.error) {
        this.api = new KenApi(cfg);
        try {
          const [project, tasks] = await Promise.all([
            this.project?.id === cfg.projectId ? this.project : this.api.getProject(),
            this.api.listTasks(),
          ]);
          this.project = project;
          this.groups = groupByStatus(tasks);
        } catch (err) {
          this.error = `kenboard injoignable : ${err instanceof Error ? err.message : err}`;
        }
      }
    }
    this.emitter.fire(undefined);
  }

  /**
   * @param {Node} node
   * @returns {vscode.TreeItem}
   */
  getTreeItem(node) {
    if (node.kind === 'message') {
      const item = new vscode.TreeItem(node.text);
      item.iconPath = new vscode.ThemeIcon('warning');
      return item;
    }
    if (node.kind === 'status') {
      const item = new vscode.TreeItem(
        node.status,
        node.status === 'review'
          ? vscode.TreeItemCollapsibleState.Collapsed
          : vscode.TreeItemCollapsibleState.Expanded,
      );
      item.id = `status:${node.status}`;
      item.description = String(node.tasks.length);
      return item;
    }
    const { task } = node;
    const item = new vscode.TreeItem(taskLabel(task));
    item.id = `task:${task.id}`;
    item.description = task.who || undefined;
    item.tooltip = new vscode.MarkdownString(
      `**#${task.id} ${task.title}**\n\n${task.status}${task.who ? ` · ${task.who}` : ''}`,
    );
    item.contextValue = 'task';
    item.command = {
      command: 'kenboard.showTask',
      title: 'Afficher le détail',
      arguments: [node],
    };
    return item;
  }

  /**
   * @param {Node} [node]
   * @returns {Node[]}
   */
  getChildren(node) {
    if (node?.kind === 'status') return node.tasks.map((task) => ({ kind: 'task', task }));
    if (node) return [];
    if (this.error) return [{ kind: 'message', text: this.error }];
    if (!this.groups) return [];
    return TREE_STATUSES.map((status) => ({
      kind: 'status',
      status,
      tasks: this.groups?.get(status) ?? [],
    }));
  }
}

/** @param {vscode.ExtensionContext} context */
function activate(context) {
  const provider = new TaskTreeProvider();
  const view = vscode.window.createTreeView('kenboard.tasks', { treeDataProvider: provider });

  // One detail panel, reused from task to task (like the markdown preview).
  /** @type {vscode.WebviewPanel | null} */
  let panel = null;
  /** @type {number | null} */
  let shownId = null;
  /** @type {string} */
  let shownKey = '';

  /** Tree + open detail: both reloaded from the API. */
  const refresh = async () => {
    await provider.reload();
    view.title = provider.project ? `Tâches — ${provider.project.name}` : 'Tâches';
    await reloadShown();
  };

  /** @param {number} [taskId] */
  const webUrl = (taskId) =>
    provider.api && provider.project
      ? boardUrl(provider.api.cfg.baseUrl, provider.project.cat_id, taskId)
      : null;

  /** @param {number} [taskId] */
  const open = (taskId) => {
    const url = webUrl(taskId);
    if (url) vscode.env.openExternal(vscode.Uri.parse(url));
  };

  /**
   * Render ``task`` in the open panel. Skipped when nothing changed, so a
   * periodic refresh does not reset the reader's scroll position.
   * @param {Task} task
   */
  const renderTask = (task) => {
    if (!panel || !provider.api) return;
    const key = JSON.stringify(task);
    if (task.id === shownId && key === shownKey) return;
    shownId = task.id;
    shownKey = key;
    panel.title = `#${task.id} ${task.title}`;
    // Markdown is rendered in the webview by the site's own marked + DOMPurify
    // (media/vendor/, copied from static/ at package time) for the same look.
    const { webview } = panel;
    /** @param {string[]} parts */
    const media = (...parts) =>
      webview.asWebviewUri(vscode.Uri.joinPath(context.extensionUri, 'media', ...parts)).toString();
    webview.html = detailHtml({
      task,
      url: webUrl(task.id) || provider.api.cfg.baseUrl,
      cspSource: webview.cspSource,
      nonce: crypto.randomBytes(16).toString('base64'),
      iconUri: media('kenboard.png'),
      scriptUris: [
        media('vendor', 'marked.min.js'),
        media('vendor', 'dompurify.min.js'),
        media('render.js'),
      ],
    });
  };

  /**
   * Re-fetch the task shown in the panel (GET /api/v1/tasks/<id>, readable by
   * a per-project key since ken #1129). On error the current render stays.
   */
  const reloadShown = async () => {
    if (!panel || shownId === null || !provider.api) return;
    try {
      renderTask(await provider.api.getTask(shownId));
    } catch {
      // Board unreachable or task deleted: keep what is displayed; the tree
      // already reports connectivity problems.
    }
  };

  /**
   * Open (or reuse) the detail panel on ``task``: render the list data at once,
   * then replace it with the fresh copy from the API.
   * @param {Task} task
   */
  const showTask = async (task) => {
    if (!provider.api) return;
    if (!panel) {
      panel = vscode.window.createWebviewPanel(
        'kenboard.task',
        '',
        { viewColumn: vscode.ViewColumn.Active, preserveFocus: false },
        {
          enableScripts: true,
          enableFindWidget: true,
          localResourceRoots: [vscode.Uri.joinPath(context.extensionUri, 'media')],
        },
      );
      panel.iconPath = vscode.Uri.joinPath(context.extensionUri, 'media', 'kenboard.png');
      panel.onDidDispose(() => {
        panel = null;
        shownId = null;
        shownKey = '';
      });
      // Back on the tab after a while: show the current state of the task.
      panel.onDidChangeViewState((e) => {
        if (e.webviewPanel.visible) void reloadShown();
      });
    } else {
      panel.reveal(undefined, false);
    }
    renderTask(task);
    await reloadShown();
  };

  // Periodic refresh like the board page (60s by default, 0 disables it);
  // skipped while the VS Code window is in the background.
  const autoRefreshSeconds = vscode.workspace
    .getConfiguration('kenboard')
    .get('autoRefreshSeconds', 60);
  if (autoRefreshSeconds > 0) {
    const timer = setInterval(() => {
      if (vscode.window.state.focused) void refresh();
    }, autoRefreshSeconds * 1000);
    context.subscriptions.push({ dispose: () => clearInterval(timer) });
  }

  context.subscriptions.push(
    view,
    vscode.commands.registerCommand('kenboard.refresh', refresh),
    vscode.commands.registerCommand('kenboard.openBoard', () => open()),
    vscode.commands.registerCommand('kenboard.showTask', (/** @type {Node} */ node) => {
      if (node?.kind === 'task') void showTask(node.task);
    }),
    vscode.commands.registerCommand('kenboard.openTask', (/** @type {Node} */ node) => {
      if (node?.kind === 'task') open(node.task.id);
    }),
    vscode.commands.registerCommand('kenboard.moveTo', async (/** @type {Node} */ node) => {
      if (node?.kind !== 'task' || !provider.api) return;
      const { task } = node;
      const status = await vscode.window.showQuickPick(
        ALL_STATUSES.filter((s) => s !== task.status),
        { placeHolder: `Déplacer #${task.id} (${task.status}) vers…` },
      );
      if (!status) return;
      try {
        await provider.api.setStatus(task.id, status);
        vscode.window.setStatusBarMessage(`kenboard : #${task.id} → ${status}`, 3000);
      } catch (err) {
        vscode.window.showErrorMessage(`kenboard : ${err instanceof Error ? err.message : err}`);
      }
      // Reloads the tree and, if it is this task, the open detail.
      await refresh();
    }),
    vscode.workspace.onDidChangeWorkspaceFolders(refresh),
  );

  void refresh();
}

function deactivate() {}

module.exports = { activate, deactivate };
