<template>
  <footer class="footer">
    <p class="footer-link" v-if="link.length">
      <span v-for="(item, index) in link" :key="index" class="footer-link-list">
        <a :href="item.href" :target="item.target" class="footer-link-item">
          {{ item.name }}
        </a>
      </span>
    </p>
    <p class="footer-copyright">
      {{ $t('蓝鲸版权', { year: new Date().getFullYear(), version: version }) }}
    </p>
  </footer>
</template>

<script lang="ts">
import { Vue, Component } from 'vue-property-decorator';

@Component({ name: 'nm-footer' })

export default class NmFooter extends Vue {
  private link: { name: string, href: string, target?: string }[] = [];

  private created() {
    this.version =  window.PROJECT_CONFIG.VERSION;
    if (window.PROJECT_CONFIG.RUN_VER === 'ieod') {
      this.link = [
        {
          name: window.i18n.t('联系BK助手'),
          href: window.PROJECT_CONFIG.WXWORK_UIN,
          target: '_blank',
        },
        {
          name: window.i18n.t('蓝鲸桌面'),
          href: window.PROJECT_CONFIG.DESTOP_URL,
          target: '_blank',
        },
      ];
    }
  }
}
</script>

<style lang="postcss" scoped>
.footer {
  position: absolute;
  padding: 0 24px;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  padding: 19px 0;
  text-align: center;
  p {
    line-height: 1;
  }
  &-link {
    margin-bottom: 8px;
    &-list {
      padding: 0 4px;
      &:not(:last-child) {
        border-right: 1px solid #3a84ff;
      }
    }
    &-item {
      display: inline-block;
      color: #3a84ff;
    }
  }
  &-copyright {
    color: #979ba5;
  }
}
</style>
