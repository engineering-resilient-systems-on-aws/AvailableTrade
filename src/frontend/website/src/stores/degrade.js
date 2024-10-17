import {defineStore} from "pinia";

export const useDegradingStore = defineStore('degrade', {
  state: () => ({
    account_open_available: true, account_open_failure_count: 0
  }),
  getters: {
    accountOpenAvailable(state) {
      return state.account_open_available;
    }
  },
  actions: {
    monitorAccountOpenAvailability() {
      setInterval(this.accountOpenHeartbeat, 5000)
      // set availability immediately to activate, then monitor the heartbeat
      this.account_open_available = this.accountOpenHeartbeat().ok
    },
    async accountOpenHeartbeat() {
      let ok = true
      try {
        let response = await this.optionsHeartbeat(import.meta.env.VITE_NEW_ACCOUNT_ENDPOINT)
        ok = response.ok
      } catch (error) {
        console.error(error)
        ok = false
        //this.account_open_available = false;
      }
      if (ok) {
        this.account_open_available = true;
        this.account_open_failure_count = 0;
      } else {
        this.account_open_failure_count += 1;
        if (this.account_open_failure_count > 5) {
          this.account_open_available = false;
        }
      }
    },
    async optionsHeartbeat(endpoint) {
      const options = {};
      const controller = new AbortController();
      const {timeout = 1000} = options;
      const id = setTimeout(() => controller.abort(), timeout)
      return fetch(endpoint, {
        ...options,
        method: "OPTIONS",
        mode: "cors",
        cache: "no-cache",
      })
    }
  },
})