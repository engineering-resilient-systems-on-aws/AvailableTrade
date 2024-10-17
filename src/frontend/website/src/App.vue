<script setup>
import {RouterLink, RouterView} from 'vue-router'
</script>

<template>
  <div class="row">
    <div class="col-md-1"></div>
    <div class="col-md-2">
      <RouterLink to="/">
        <img src="../public/AvailableTrade.png" height="75">
        </RouterLink>
    </div>
    <div class="col-md-7">
      <nav>
        <h1>Resilient Systems on AWS</h1>
        <RouterLink to="/account_open" class="header-nav">Open Account</RouterLink> |
        <RouterLink to="/trade_stock" class="header-nav">Trade</RouterLink> |
        <RouterLink to="/insights" class="header-nav">Insights</RouterLink> |
        <RouterLink to="/utilities" class="header-nav">Utilities</RouterLink>
      </nav>
    </div>
    <div class="col-md-2"></div>
  </div>
  <RouterView/>

</template>

