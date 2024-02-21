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
import i18n, { TranslateResult } from '@/setup';

interface ICopyItem {
  id: string;
  name: TranslateResult;
  testId: string;
}

function createItem(type: 'checked' | 'all', ipType: 'IPv4' | 'IPv6', hasCloud = false) {
  const item: ICopyItem = {
    id: `${type}_${ipType}`,
    name: ipType,
    testId: 'moreItem',
  };
  if (hasCloud) {
    item.id = `${item.id}_cloud`;
    item.name = i18n.t('管控区域IP复制', [ipType]);
  }
  return item;
}

export const checkedChildList = window.$DHCP
  ? [
    createItem('checked', 'IPv4'),
    createItem('checked', 'IPv6'),
    createItem('checked', 'IPv4', true),
    createItem('checked', 'IPv6', true),
  ]
  : [
    createItem('checked', 'IPv4'),
    createItem('checked', 'IPv4', true),
  ];
export const allChildList = window.$DHCP
  ? [
    createItem('all', 'IPv4'),
    createItem('all', 'IPv6'),
    createItem('all', 'IPv4', true),
    createItem('all', 'IPv6', true),
  ]
  : [
    createItem('all', 'IPv4'),
    createItem('all', 'IPv4', true),
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
  @Prop({ type: Boolean, default: true }) protected readonly associateCloud!: boolean;

  @Ref('copyIpRef') private readonly copyIpRef!: any;

  private openDropdown = false;
  private loading = false;

  protected get menuList() {
    if (this.list?.length) {
      return this.$DHCP
        ? this.list.map((item => ({
          ...item,
          child: item.child
            ? this.pickChildren(item.child)
            : this.pickChildren(allChildList.map(child => ({
              ...child,
              id: `${item.id}_${child.id}`,
            }))),
        }))) : this.list;
    }
    return  [
      {
        id: 'select_IP',
        name: i18n.t('勾选IP'),
        disabled: this.notSelected,
        testId: 'moreItem',
        testKey: 'checkedIp',
        child: this.pickChildren(checkedChildList),
      },
      {
        id: 'all_IP',
        name: i18n.t('所有IP'),
        testId: 'moreItem',
        testKey: 'allIp',
        child: this.pickChildren(allChildList),
      },
    ];
  }

  public pickChildren(list: ICopyItem[]) {
    return this.associateCloud
      ? list
      : list.filter(child => !child.id.includes('_cloud'));
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
          message: i18n.t('复制成功Object', [list.length, type.includes('v6') ? 'IPv6' : 'IPv4']),
        });
      });
    }
  }
}
</script>
