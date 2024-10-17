<template>
  <main>
  <div class="row">
    <div class="col-md-3"></div>
    <div class="col-md-5">
      <h1 class="page-header">Discover opportunities</h1>
      <p v-if="customer.isRegistered">Current Customer: {{ customer.firstName }}</p>
      <p>This page is a placeholder for Trading Insights</p>
  </div>
  </div>
  </main>
</template>

<script setup>
import { useCustomerStore } from "@/stores/customer.js";
import {useUserMonitorStore} from "@/stores/user_monitor.js";
import {onErrorCaptured} from "vue";

const customer = useCustomerStore();
const monitorStore = useUserMonitorStore();
onErrorCaptured((error) => { monitorStore.recordError(error) });
</script>