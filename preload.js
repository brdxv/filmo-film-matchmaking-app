
const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("FILMO_CONFIG", {
  apiBase: "http://127.0.0.1:5050"
});
