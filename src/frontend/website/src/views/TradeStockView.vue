<template>
  <div class="row" v-if="customer.isRegistered">
    <div class="col-md-3"></div>
    <div class="col-md-5">
      <h1>Hello {{ customer.firstName }} {{ customer.lastName }}</h1>
      <p>You are ready to place a trade. For demonstration purposes, several of your trade parameters are fixed.
        Simply specify how many shares you'd like to buy, then submit the trade.</p>
      <span class="error">{{ submit_failure }}</span>
      <span class="error">{{ trade_message }}</span>
      <form id="trade-stock" class="form-inline" v-on:submit.prevent="tradeStock()">
        <span class="error">{{ errors.share_count }}</span><br/>
        <input id="share_count" type="text" v-model="share_count" v-bind="share_count_attrs"/>
        <br/>
        <br/>
        <button id="form_submit" class="btn btn-primary">Purchase shares</button>
      </form>
    </div>
  </div>
  <div class="row" v-else>
    <div class="col-md-3"></div>
    <div class="col-md-5">
      <h1 class="page-header">Open an Account</h1>
      To get started with trading, open an account, then come back here.
    </div>
  </div>
</template>

<script setup>
import {useCustomerStore} from "@/stores/customer.js";
import {useUserMonitorStore} from "@/stores/user_monitor.js";
import {onErrorCaptured, ref} from "vue";
import {useForm} from 'vee-validate';
import * as yup from 'yup';
import {v4 as uuidv4} from 'uuid'

const customer = useCustomerStore();
const monitorStore = useUserMonitorStore();
onErrorCaptured((error) => {
  monitorStore.recordError(error)
});

const schema = yup.object({
  customer_id: yup.string().required(),
  ticker: yup.string().required(),
  transaction_type: yup.string().required(),
  current_price: yup.number().positive().required(),
  share_count: yup.number().integer().required().min(1).max(1000)
})

const {values, errors, defineField, handleSubmit} = useForm({
  validationSchema: schema
});

const [customer_id] = defineField('customer_id')
const [ticker] = defineField('ticker')
const [transaction_type] = defineField('transaction_type')
const [current_price] = defineField('current_price')
const [share_count, share_count_attrs] = defineField('share_count')
const [request_id] = defineField('request_id')
const submit_failure = ref('')
const trade_message = ref('')

function setForm() {
  request_id.value = uuidv4();
  customer_id.value = customer.user_id;
  transaction_type.value = "buy";
  ticker.value = 'IPAY';
  current_price.value = '40.06';
}

setForm()

const tradeStock = handleSubmit(values => {
  processTrade()
})

async function processTrade() {
  let json = {}
  try {
    json = await postTrade(values);
    console.log("post trade output: " + JSON.stringify(json));
  } catch (error) {
    console.log(error);
    if (error.name === "TimeoutError") {
    console.error("Timeout: It took more than 5 seconds to get the result!");
  } else if (error.name === "AbortError") {
    console.error(
      "Fetch aborted by user action (browser stop button, closing tab, etc.",
    );
  } else if (error.name === "TypeError") {
    console.error("AbortSignal.timeout() method is not supported");
  } else {
    // A network error, or some other problem.
    console.error(`Error: type: ${error.name}, message: ${error.message}`);
  }
  }

  if (json.ok) {
    let result = await json.json()
    console.log(result);
    trade_message.value = "Your trade of " + result["share_count"] + " shares was " + result["status"];
    setForm()
  } else {
    const message = "Trade not executed, service failed";
    console.log(message);
    submit_failure.value = message;
  }
}

async function postTrade(data = {}, options = {}) {

  const request_json = {
    request_id: data.request_id,
    customer_id: "4",
    ticker: data.ticker,
    transaction_type: data.transaction_type,
    current_price: data.current_price,
    share_count: data.share_count
  }

  console.log(request_json)
  console.log("Endopint: " + import.meta.env.VITE_TRADE_STOCK_ENDPOINT)  

  return fetch(import.meta.env.VITE_TRADE_STOCK_ENDPOINT + "trade/", {
    signal: AbortSignal.timeout(3000),
    method: "PUT",
    mode: "cors",
    cache: "no-cache",
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(request_json)
  });
}
</script>