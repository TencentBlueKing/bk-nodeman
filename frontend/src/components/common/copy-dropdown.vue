<template>
  <bk-dropdown-menu
    ref="copyIpRef"
    ext-cls="copy-dropdown"
    trigger="click"
    font-size="medium"
    :disabled="disabled || loading"
    @show="openDropdown = true"
    @hide="openDropdown = false">
    <bk-button
      class="dropdown-btn"
      slot="dropdown-trigger"
      :disabled="disabled || loading"
      v-test="'copy'">
      <!-- :loading="loading" -->
      <span class="icon-down-wrapper">
        <span>{{ $t('复制') }}</span>
        <i :class="['bk-icon icon-angle-down', { 'icon-flip': openDropdown }]"></i>
      </span>
    </bk-button>
    <AssociateList slot="dropdown-content" :list="menuList" @click="handleClick" />
  </bk-dropdown-menu>
</template>
<script lang="ts">
import { Component, Vue, Prop, Ref } from 'vue-property-decorator';
import AssociateList, { IAssociateItem } from '@/components/common/associate-list.vue';
import { copyText } from '@/common/util';

export const defaultList = [
  { id: 'all_IPv4', name: window.i18n.t('复制IPv4'), testId: 'moreItem' },
  { id: 'all_IPv6', name: window.i18n.t('复制IPv6'), testId: 'moreItem' },
];
export const checkedChildList = [
  { id: 'checked_IPv4', name: 'IPv4', testId: 'moreItem' },
  { id: 'checked_IPv6', name: 'IPv6', testId: 'moreItem' },
];
export const allChildList = [
  { id: 'all_IPv4', name: 'IPv4', testId: 'moreItem' },
  { id: 'all_IPv6', name: 'IPv6', testId: 'moreItem' },
];

@Component({
  name: 'CopyDropdown',
  components: { AssociateList },
})

export default class CopyDropdown extends Vue {
  // @Prop({ type: Boolean, default: false }) protected readonly loading!: boolean;
  @Prop({ type: Boolean, default: false }) protected readonly disabled!: boolean;
  @Prop({ type: Boolean, default: false }) protected readonly notSelected!: boolean;
  @Prop({ type: Boolean, default: false }) protected readonly disableCheck!: boolean;
  @Prop({ type: Array, default: () => [] }) protected readonly list!: IAssociateItem[];
  @Prop({ type: Function, required: true }) protected readonly getIps!: (type: string) => Promise<string[]>;

  @Ref('copyIpRef') private readonly copyIpRef!: any;

  private openDropdown = false;
  private loading = false;

  protected get menuList() {
    if (this.list?.length) {
      return this.list;
    }
    return  this.disableCheck
      ? defaultList
      : [
        {
          id: 'select_IP',
          name: this.$t('勾选IP'),
          disabled: this.notSelected,
          testId: 'moreItem',
          testKey: 'checkedIp',
          child: checkedChildList,
        },
        {
          id: 'all_IP',
          name: this.$t('所有IP'),
          testId: 'moreItem',
          testKey: 'allIp',
          child: allChildList,
        },
      ];
  }

  public async handleClick(type: string, item: IAssociateItem) {
    if (!item.disabled && !item.child?.length) {
      this.loading = true;
      const list = await this.getIps(type);
      this.copyIpRef.hide();
      this.loading = false;
      const checkedIpText = list.join('\n');
      if (checkedIpText) {
        copyText(checkedIpText, () => {
          this.$bkMessage({
            theme: 'success',
            message: this.$t('复制成功Object', [list.length, type.includes('v6') ? 'IPv6' : 'IPv4']),
          });
        });
      } else {
        this.$bkMessage({
          theme: 'error',
          message: this.$t('复制失败common'),
        });
      }
    }
  }
}
</script>
