import { defineStore} from "pinia";


export const useCustomerStore = defineStore('customer', {
  state: () => ({
     first_name: '', last_name: '', registered: false, account_request_token: '', user_id: ''
  }),
  getters: {
    firstName(state) {
      return state.first_name;
    },
    lastName(state) {
      return state.last_name;
    },
    accountReqeustToken(state) {
      return state.account_request_token;
    },
    userId(state) {
      return state.user_id;
    },
    isRegistered(state) {
      return state.registered;
    }
  },
  actions: {
    refresh(customer_record) {
      console.log("refresh", customer_record);
      this.first_name = customer_record.first_name;
      this.last_name = customer_record.last_name;
      this.account_request_token = customer_record.request_token;
      this.user_id = customer_record.user_id;
    },
    confirmRegistration() {
      this.registered = true;
    }
  },
})