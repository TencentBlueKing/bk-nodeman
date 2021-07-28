<template>
  <div>
    <div class="div-input" contenteditable></div>
    <input type="password">
  </div>
</template>
<script lang="ts">
import { Vue, Component } from 'vue-property-decorator';

@Component({ name: 'password' })
export default class Password extends Vue {}

</script>
<style lang="postcss" scoped>
  .div-input {
    height: 32px;
    line-height: 30px;
    color: #63656e;
    background-color: #fff;
    border-radius: 2px;
    width: 100%;
    font-size: 12px;
    border: 1px solid #c4c6cc;
    padding: 0 10px;
    text-align: left;
    vertical-align: middle;
    outline: none;
    resize: none;
    transition: border .2s linear;
    &:focus {
      border-color: #3a84ff;
      background-color: #fff;
    }
  }
</style>
