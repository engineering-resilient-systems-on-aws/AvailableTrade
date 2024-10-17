<template>

  <main>
    <span v-if="degradeStore.accountOpenAvailable">
    <div class="row" v-if="customer.isRegistered">
      <div class="col-md-3"></div>
      <div class="col-md-4">Welcome <strong>{{ customer.firstName }} {{ customer.lastName }}</strong>, you're ready to trade!</div>
    </div>
    <form id="account-open" class="form-inline" v-on:submit.prevent="openAccount()" v-else>
      <div class="row">
        <div class="col-md-3"></div>
        <div class="col-md-4">
          <h1 class="page-header">New Trading Account</h1>
          <!-- Gracefully Degrading Features submit_failure example -->
<!--          <span class="error">{{ submit_failure }}</span>-->
        </div>
      </div>
      <div class="row">
        <div class="col-md-3"></div>
        <div class="col-md-2">
          <label for="first_name">First Name</label>
        </div>
        <div class="col-md-3">
          <span class="error">{{ errors.first_name }}</span>
          <input id="first_name" type="text" v-model="first_name" v-bind="first_name_attrs" autocomplete="given-name"/>
        </div>
      </div>
      <div class="row">
        &nbsp;
      </div>
      <div class="row">
        <div class="col-md-3"></div>
        <div class="col-md-2">
          <label for="last_name">Last Name</label>
        </div>
        <div class="col-md-3">
          <span class="error">{{ errors.last_name }}</span>
          <input id="last_name" type="text" v-model="last_name" v-bind="last_name_attrs" autocomplete="family-name"/>
        </div>
      </div>
      <div class="row">
        &nbsp;
      </div>
      <div class="row">
        <div class="col-md-3"></div>
        <div class="col-md-2">
          <label for="dividends">Dividends</label></div>
        <div class="col-md-3">
          <span class="error">{{ errors.dividends }}</span>
          <select id="dividends" v-model="dividends" v-bind="dividends_attrs" style="color: black">
            <option value="">--Select--</option>
            <option value="reinvest">Reinvest</option>
            <option value="cash">Cash</option>
          </select>
        </div>
      </div>
      <div class="row">
        &nbsp;
      </div>
      <div class="row">
        <div class="col-md-3"></div>
        <div class="col-md-2">
          <label for="time_horizon">Time Horizon</label></div>
        <div class="col-md-3">
          <span class="error">{{ errors.time_horizon }}</span>
          <select id="time_horizon" v-model="time_horizon" v-bind="time_horizon_attrs" style="color: black">
            <option value="">--Select--</option>
            <option value="5">5 years</option>
            <option value="10">10 years</option>
            <option value="15">15 years</option>
            <option value="20">20 years</option>
            <option value="25">25 years</option>
            <option value="30">30 years</option>
          </select>
        </div>
      </div>
      <div class="row">
        &nbsp;
      </div>
      <div class="row">
        <div class="col-md-3"></div>
        <div class="col-md-4">
          <span class="error">{{ errors.liquidity }}</span>
          <fieldset>
            <legend>Choose a Liquidity Goal</legend>
            <label for="liquidity.low">Low</label>
            <input id="liquidity.low" name="liquidity" type="radio" value="low" v-model="liquidity"
                   v-bind="liquidity_attrs"/>
            &nbsp;
            <label for="liquidity.high">High</label>
            <input id="liquidity.high" name="liquidity" type="radio" value="high" v-model="liquidity"
                   v-bind="liquidity_attrs"/>
          </fieldset>
        </div>
      </div>
      <div class="row">
        &nbsp;
      </div>

      <div class="row">
        <div class="col-md-3"></div>
        <div class="col-md-4">
          <span class="error">{{ errors.risk_tolerance }}</span>
          <fieldset>
            <legend>Select your Risk Tolerance</legend>
            <label for="risk_tolerance.low">Low</label>
            <input id="risk_tolerance.low" name="risk_tolerance" type="radio" value="low" v-model="risk_tolerance"
                   v-bind="risk_tolerance_attrs">&nbsp;
            <label for="risk_tolerance.low">Medium</label>
            <input id="risk_tolerance.medium" name="risk_tolerance" type="radio" value="medium" v-model="risk_tolerance"
                   v-bind="risk_tolerance_attrs">&nbsp;
            <label for="risk_tolerance.low">High</label>
            <input id="risk_tolerance.high" name="risk_tolerance" type="radio" value="high" v-model="risk_tolerance"
                   v-bind="risk_tolerance_attrs">
          </fieldset>
        </div>
      </div>
      <div class="row">
        &nbsp;
      </div>
      <!-- A nicer form would collect beneficiaries into a list and validate the percentage totals 100% -->
      <div class="row">
        <div class="col-md-3"></div>
        <div class="col-md-4">
          <button id="form_submit" class="btn btn-primary">Create Account</button>
        </div>
      </div>
    </form>
  </span>


  <div class="row" v-else>
    <div class="col-md-3"></div>
    <div class="col-md-4">
      <h4 class="page-header">New Account Form Unavailable</h4>
      Our account open service is currently available. We'll be back soon.
      In the meantime, you can still place trades, gain insights and use utilities.
      If you need to open your account now, you can still do so with our agent based telephone support.
      Please call (555) GET-WISE [(555) 438-9473]. Hold times may vary.
    </div>
  </div>
  </main>
</template>

<script setup>
import {useCustomerStore} from "@/stores/customer.js";
import {useForm} from 'vee-validate';
import * as yup from 'yup';
import {v4 as uuidv4} from 'uuid'
import {ref} from 'vue';
import {useUserMonitorStore} from "@/stores/user_monitor.js";
import {useDegradingStore} from "@/stores/degrade.js";

// For Chapter 6 Gracefully Degrading Features Uncomment this store both in AccountOpenView.vue and HomeView.vue
// const degradeStore = useDegradingStore();
// degradeStore.monitorAccountOpenAvailability();

const customer = useCustomerStore();

// Chapter 6 Real User Monitoring:
//const monitorStore = useUserMonitorStore();
//onErrorCaptured((error) => { monitorStore.recordError(error) });

const schema = yup.object({
  first_name: yup.string().required(),
  last_name: yup.string().required(),
  liquidity: yup.string().required(),
  time_horizon: yup.string().required(),
  risk_tolerance: yup.string().required(),
  dividends: yup.string().required(),
})
const {values, errors, defineField, handleSubmit} = useForm({
  validationSchema: schema
});
const [first_name, first_name_attrs] = defineField("first_name", {})
const [last_name, last_name_attrs] = defineField("last_name", {})
const [liquidity, liquidity_attrs] = defineField("liquidity", {})
const [time_horizon, time_horizon_attrs] = defineField("time_horizon", {})
const [risk_tolerance, risk_tolerance_attrs] = defineField("risk_tolerance", {})
const [dividends, dividends_attrs] = defineField("dividends", {})
const [request_token] = defineField('request_token')
const [user_id] = defineField('user_id')
request_token.value = uuidv4();
user_id.value = Math.floor(Math.random() * 9999).toString();

const submit_failure = ref('')


const openAccount = handleSubmit(values => {
  processAccount()
})

async function processAccount() {
  let json = {}
  try {
    json = await postAccount(values);
    console.log("post account output: " + JSON.stringify(json));
  } catch (error) {
    console.log(error);
  }

  if (json.ok) {
    console.log("refreshing customer and confirming registration");
    let result = await json.json()
    console.log(result);
    customer.refresh(values);
    customer.confirmRegistration();
    submit_failure.value = ''
  } else {
    const message = "New Account not created, service failed";
    console.log(message);
    submit_failure.value = message;
  }
}

async function postAccount(data = {}, options = {}) {
  // ToDo get the customer id and request token from store, demonstrate the re-use to facilitate idempotency properly
  const structured_data = {
    customer_first_name: data.first_name,
    customer_last_name: data.last_name,
    account_type: "moneymaker",
    comment: "from portal",
    request_token: data.request_token,
    user_id: "customer_" + data.user_id,
    beneficiaries: [
      {
        name: "Stub1",
        percentage: 75
      },
      {
        name: "Stub2",
        percentage: 25
      }
    ],
    suitability: {
      liquidity: data.liquidity,
      time_horizon: data.time_horizon,
      risk_tolerance: data.risk_tolerance
    }, instructions: {
      dividends: data.dividends
    }
  }
  const controller = new AbortController();
  const {timeout = 3000} = options;
  const id = setTimeout(() => controller.abort(), timeout)
  console.log("Endpoint: " + import.meta.env.VITE_NEW_ACCOUNT_ENDPOINT)
  return fetch(import.meta.env.VITE_NEW_ACCOUNT_ENDPOINT, {
    ...options,
    signal: controller.signal,
    method: "PUT",
    mode: "cors",
    cache: "no-cache",
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(structured_data)
  });
}
</script>