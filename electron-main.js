const { app, BrowserWindow, dialog, Menu } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const http = require("http");

let backendProcess = null;

function getPythonCommandAndArgs(scriptPath) {
  if (process.platform === "win32") return { command: "py", args: ["-3", scriptPath] };
  return { command: "python3", args: [scriptPath] };
}

function startBackend() {
  const backendDir = path.join(__dirname, "backend");
  const backendPath = path.join(backendDir, "app.py");
  const py = getPythonCommandAndArgs(backendPath);

  backendProcess = spawn(py.command, py.args, {
    cwd: backendDir,
    shell: false,
    windowsHide: true,
    stdio: "pipe"
  });

  backendProcess.stdout.on("data", d => console.log(`[Python] ${d}`));
  backendProcess.stderr.on("data", d => console.error(`[Python Error] ${d}`));
  backendProcess.on("close", code => console.log(`Python backend exited with code ${code}`));
}

function waitForBackend(retries = 80) {
  return new Promise((resolve, reject) => {
    const test = n =>
      http
        .get("http://127.0.0.1:5050/", () => resolve(true))
        .on("error", () =>
          n <= 0
            ? reject(new Error("backend failed"))
            : setTimeout(() => test(n - 1), 250)
        );

    test(retries);
  });
}

function createMenu() {
  const template = [
    {
      label: "File",
      submenu: [
        { role: "quit" }
      ]
    },
    {
      label: "Edit",
      submenu: [
        { role: "undo" },
        { role: "redo" },
        { type: "separator" },
        { role: "cut" },
        { role: "copy" },
        { role: "paste" },
        { role: "selectAll" }
      ]
    },
    {
      label: "View",
      submenu: [
        { role: "reload" },
        { role: "forceReload" },
        { role: "toggleDevTools" },
        { type: "separator" },
        { role: "resetZoom" },
        { role: "zoomIn" },
        { role: "zoomOut" },
        { type: "separator" },
        { role: "togglefullscreen" }
      ]
    },
    {
      label: "Window",
      submenu: [
        { role: "minimize" },
        { role: "close" }
      ]
    },
    {
      label: "Help",
      submenu: [
        {
          label: "About FILMO",
          click: () => {
            dialog.showMessageBox({
              type: "info",
              title: "About FILMO",
              message: "FILMO",
              detail: "A Matchmaking App for Film Lovers"
            });
          }
        }
      ]
    }
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1120,
    height: 820,
    minWidth: 360,
    minHeight: 560,
    title: "FILMO",
    backgroundColor: "#f7f4ec",

    frame: true,
    autoHideMenuBar: true,

    webPreferences: {
      preload: path.join(__dirname, "frontend", "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  win.loadFile(path.join(__dirname, "frontend", "index.html"));
}

app.whenReady().then(async () => {
  createMenu();
  startBackend();

  try {
    await waitForBackend();
    createWindow();
  } catch (e) {
    dialog.showErrorBox(
      "FILMO backend error",
      "Python backend failed to start. Run: py -m pip install -r backend/requirements.txt"
    );
    app.quit();
  }
});

app.on("window-all-closed", () => {
  if (backendProcess) backendProcess.kill();
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  if (backendProcess) backendProcess.kill();
});