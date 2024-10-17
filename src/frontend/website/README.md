# portal-integrated-ui

TODO: you need to setup environment configs 
1. for local, you'll build it by hand
2. for deployments, you'll build it with python in the cdk deployment, you'll fetch all the parameters from the parameter store, which requires all your service must register endpoints in the parameter store. This helps resilience because we'll fail the deployment if expected parameters are not configured, and we don't ever manage parameters by hand (except locally). Once you code this, you can probably address with the script for local too. 

## Customize configuration

https://cli.vuejs.org/guide/mode-and-env.html#modes
See [Vite Configuration Reference](https://vitejs.dev/config/).

## build out CDK deployment configuration, sync with Jen on this. 

## Project Setup

```sh
npm install
```

### Compile and Hot-Reload for Development

```sh
npm run dev
```

### Compile and Minify for Production

```sh
npm run build
```
