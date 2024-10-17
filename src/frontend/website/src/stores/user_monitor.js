import {ref, computed} from 'vue'
import {defineStore} from 'pinia'
import {AwsRum} from 'aws-rum-web';

const config = {
            sessionSampleRate: 1,
            identityPoolId: "us-east-1:7d6deffb-1f1d-4bb9-8266-2d1e88d8016d",
            endpoint: "https://dataplane.rum.us-east-1.amazonaws.com",
            telemetries: ["errors", "performance", "http"],
            allowCookies: true,
            enableXRay: true
        }
        const APPLICATION_ID = import.meta.env.VITE_RUM_APPLICATION_ID;
        const APPLICATION_VERSION = '1.0.0';
        const APPLICATION_REGION = 'us-east-1';
export const useUserMonitorStore = defineStore('user_monitor', {
    state: () => ({
     aws_rum: new AwsRum(APPLICATION_ID, APPLICATION_VERSION,APPLICATION_REGION,config)
    }),
    getters: {
        monitor(state) {
            return state.aws_rum;
        }
    },
    actions: {
        /**
         * Manually record a page view.
         * Rum records page views added to HTML 5 history be default, so it is rare you'd need to this
         * @param page
         */
        recordPageView(page) {
            console.log("recording page", page)
            this.aws_rum.recordPageView(page)
        },

        /**d
         * Record errors.
         * Allows you to monitor, measure and alarm on UI errors.
         * Use this either with the vuejs onErrorCaptured lifecycle hook, or in catch blocks.
         * It is very common that you'd need to use this.
         * @param error
         */
        recordError(error) {
            console.log("recording page", error)
            this.aws_rum.recordError(error)
        }

    }
})
