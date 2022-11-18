<template>
  <div class="empty-service-box">
    <div class="flex-top"></div>
    <div class="empty-service-content" :style="{ width: width ? `${width}px` : 'auto' }">
      <div class="empty-top">
        <img src="../../images/not-data.png" alt="">
      </div>
      <h3 class="empty-title">{{ displayTitle }}</h3>
      <p class="empty-desc">
        <!-- <section>{{ descPath }}</section> -->
        <i18n :path="displayDescSlot">
          <bk-button text theme="primary" class="reset-icon-btn" @click="handleClick">
            <span class="flex-content">
              {{ $t('配置平台') }}<i class="nodeman-icon nc-jump-link"></i>
            </span>
          </bk-button>
        </i18n>
      </p>
    </div>
    <div class="flex-bottom"></div>
  </div>
</template>

<script>
export default {
  name: 'EmptyServiceBox',
  props: {
    width: {
      type: [String, Number],
      default: '',
    },
    type: {
      type: String,
      default: 'instance',
    },
    info: {
      type: Object,
      default: () => ({ bk_obj_id: '', bk_inst_id: '' }),
    },
    title: {
      type: String,
      default: '',
    },
    desc: {
      type: String,
      default: '',
    },
    descSlot: {
      type: String,
      default: '',
    },
  },
  computed: {
    displayTitle() {
      return this.title || this.$t('当前业务暂无服务模版');
    },
    descPath() {
      return this.desc || this.$t('业务暂无服务模版path');
    },
    displayDescSlot() {
      return this.descSlot || '业务暂无服务模版slot';
    },
  },
  methods: {
    handleClick() {
      this.$emit('click-link');
    },
  },
};
</script>

<style lang="postcss" scoped>
  .empty-service-box {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    height: 100%;

    .flex-top {
      flex: 2;
    }

    .flex-bottom {
      flex: 3;
    }

    .empty-service-content {
      display: flex;
      flex-direction: column;
      align-items: center;
      height: 230px;
      text-align: center;
    }
    .empty-top {
      max-width: 200px;
      img {
        width: 100%;
      }
    }

    .empty-title {
      margin: 20px 0 0 0;
      line-height: 26px;
      font-size: 20px;
      font-weight: normal;
      color: #63656e;
    }

    .empty-desc {
      margin: 16px 0 0 0;
      line-height: 24px;
      font-size: 14px;
      color: #979ba5;
    }
  }
</style>
