import { api, waitForSidecar } from "$lib/api";

class ConnectionStore {
  connected = $state(false);
  connectionError = $state("");
  collectionCount = $state(0);

  async refreshStatus() {
    try {
      const status = await api.status();
      this.collectionCount = status.collection_count;
      this.connected = true;
      this.connectionError = "";
    } catch (e) {
      this.connected = false;
      this.connectionError = e instanceof Error ? e.message : "Sidecar unreachable";
    }
  }

  async connect() {
    this.connectionError = "";
    const ready = await waitForSidecar();
    if (!ready) {
      this.connectionError =
        "Sidecar failed to start. Check that .venv exists and Ollama is running.";
      return;
    }
    await this.refreshStatus();
  }
}

export const connection = new ConnectionStore();