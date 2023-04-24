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
import { asyncCopyText } from '@/common/util';

export const checkedChildList = window.$DHCP
  ? [
    { id: 'checked_IPv4', name: 'IPv4', testId: 'moreItem' },
    { id: 'checked_IPv6', name: 'IPv6', testId: 'moreItem' },
  ]
  : [
    { id: 'checked_IPv4', name: 'IPv4', testId: 'moreItem' },
  ];
export const allChildList = window.$DHCP
  ? [
    { id: 'all_IPv4', name: 'IPv4', testId: 'moreItem' },
    { id: 'all_IPv6', name: 'IPv6', testId: 'moreItem' },
  ]
  : [
    { id: 'all_IPv4', name: 'IPv4', testId: 'moreItem' },
  ];

@Component({
  name: 'CopyDropdown',
  components: { AssociateList },
})

export default class CopyDropdown extends Vue {
  @Prop({ type: Boolean, default: false }) protected readonly disabled!: boolean;
  @Prop({ type: Boolean, default: false }) protected readonly notSelected!: boolean;
  @Prop({ type: Array, default: () => [] }) protected readonly list!: IAssociateItem[];
  @Prop({ type: Function, required: true }) protected readonly getIps!: (type: string) => Promise<string[]>;

  @Ref('copyIpRef') private readonly copyIpRef!: any;

  private openDropdown = false;
  private loading = false;

  protected get menuList() {
    if (this.list?.length) {
      return this.$DHCP
        ? this.list.map((item => ({
          ...item,
          child: allChildList.map(child => ({
            ...child,
            id: `${item.id}_${child.id}`,
          })),
        }))) : this.list;
    }
    return  [
      {
        id: 'select_IP',
        name: this.$t('勾选IP'),
        disabled: this.notSelected,
        testId: 'moreItem',
        testKey: 'checkedIp',
        child: this.$DHCP ? checkedChildList : [],
      },
      {
        id: 'all_IP',
        name: this.$t('所有IP'),
        testId: 'moreItem',
        testKey: 'allIp',
        child: this.$DHCP ? allChildList : [],
      },
    ];
  }

  public handleClick(type: string, item: IAssociateItem) {
    if (!item.disabled && !item.child?.length) {
      let list = [];
      asyncCopyText(async () => {
        this.loading = true;
        list = await this.getIps(type);
        this.copyIpRef.hide();
        this.loading = false;
        return list.join('\n');
      }, () => {
        this.$bkMessage({
          theme: 'success',
          message: this.$t('复制成功Object', [list.length, type.includes('v6') ? 'IPv6' : 'IPv4']),
        });
      });
    }
  }
}
</script>
