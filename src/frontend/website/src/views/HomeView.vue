<template>
  <main>
    <div class="row">
      <!-- Gracefully Degrading Features submit_failure is in the AccountOpenView, not HomeView -->
      <div class="col-md-3"></div>
      <div class="col-md-6">
        <p>Welcome to the AvailableTrade electronic trading application</p>
        <p v-if="customer.isRegistered">You are current registered as: {{ customer.firstName }}</p>
        <p v-else>To get started, open a new account</p>
      </div>
    </div>
  </main>
</template>

<script setup>
import {useCustomerStore} from "@/stores/customer.js";
import {useDegradingStore} from "@/stores/degrade.js";
import {useUserMonitorStore} from "@/stores/user_monitor.js";
import {onErrorCaptured} from "vue";

const customer = useCustomerStore();

// For Chapter 6 Gracefully Degrading Features Uncomment this store both in AccountOpenView.vue and HomeView.vue
// const degradeStore = useDegradingStore();
// degradeStore.monitorAccountOpenAvailability();

//const monitorStore = useUserMonitorStore();
/*onErrorCaptured((error) => {
  monitorStore.recordError(error)
});*/
</script>