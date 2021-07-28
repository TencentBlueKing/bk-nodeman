<template>
  <div class="exception-box">
    <img src="@/images/404.png" alt="">
    <p>没找到页面！</p>
  </div>
</template>

<script>
export default {
  data() {
    return {};
  },
};
</script>

<style scoped lang="postcss">
.exception-box {
  text-align: center;
  margin: auto;
  img {
    width: 300px;
    margin-top: 150px;
  }
  p {
    font-size: 20px;
    color: #979797;
    margin: 32px 0;
    font-weight: 400;
  }
}
</style>
