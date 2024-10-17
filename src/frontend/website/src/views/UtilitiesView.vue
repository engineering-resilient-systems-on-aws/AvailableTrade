<template>
  <main>
    <div class="row">
    <div class="col-md-3"></div>
    <div class="col-md-4">
      <h1 class="page-header">Monitor Client Errors</h1>
      <p v-if="customer.isRegistered">You are current registered as: {{ customer.firstName }}</p>
    <p>This page throws a JavaScript Error. How can you monitor, track and address client side errors?</p>
    <p>Your application is being served from <strong>{{ response }}</strong></p>
    </div>
  </div>
  </main>
</template>

<script setup>
import {useCustomerStore} from "@/stores/customer.js";
import {useUserMonitorStore} from "@/stores/user_monitor.js";
import {onErrorCaptured, ref, watchEffect} from "vue";

const customer = useCustomerStore();
const monitorStore = useUserMonitorStore();
onErrorCaptured((error) => { monitorStore.recordError(error) });

let response = ref(null)

watchEffect(async () => {
  const url = import.meta.env.VITE_TRADE_STOCK_ENDPOINT + "region-az/"
  response.value = await (await fetch(url, {
    signal: AbortSignal.timeout(3000),
    method: "GET",
    mode: "cors",
    cache: "no-cache",
    headers: {
      'Content-Type': 'application/json'
    }
  })).text()
})

let sampler = null
try {
  sampler.do_something();
} catch (error) {
  console.log(error)
}


async function getRegionAz(options = {}) {
  return fetch(import.meta.env.VITE_TRADE_STOCK_ENDPOINT + "region-az/", {
    signal: AbortSignal.timeout(3000),
    method: "GET",
    mode: "cors",
    cache: "no-cache",
    headers: {
      'Content-Type': 'application/json'
    }
  });
}
</script>
