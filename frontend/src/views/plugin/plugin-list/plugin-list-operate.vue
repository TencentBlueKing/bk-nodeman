<template>
  <section class="list-operate">
    <div class="list-operate-left h32">
      <!--插件操作-->
      <!-- <auth-component :authorized="!notOperatePermissonBiz.length" :apply-info="applyInfo">
        <template slot-scope="{ disabled }">
          <bk-button
            v-test="'operate'"
            theme="primary"
            :disabled="selectionCount || disabled"
            @click="handleOperate">
            {{ $t('批量插件操作') }}
          </bk-button>
        </template>
      </auth-component> -->
      <auth-component :authorized="!notOperatePermissonBiz.length" :apply-info="applyInfo">
        <template slot-scope="{ disabled }">
          <div style="display: flex">
            <bk-popover
              placement="bottom"
              :delay="400"
              :disabled="!(selectionCount || disabled)"
              :content="$t('请先选择主机')">
              <bk-button
                v-test="'MAIN_INSTALL_PLUGIN'"
                theme="primary"
                :disabled="selectionCount || disabled"
                @click="handleOperate('MAIN_INSTALL_PLUGIN')">
                {{ $t('安装或更新') }}
              </bk-button>
            </bk-popover>
            <bk-dropdown-menu
              class="ml10"
              trigger="click"
              font-size="medium"
              :disabled="selectionCount || disabled"
              @show="moreDropdownShow = true"
              @hide="moreDropdownShow = false">
              <bk-button class="dropdown-btn" slot="dropdown-trigger" :disabled="selectionCount || disabled">
                <div class="dropdown-trigger-btn" v-test="'operate'">
                  <div>{{ $t('批量') }}</div>
                  <i :class="['bk-icon icon-angle-down',{ 'icon-flip': moreDropdownShow }]"></i>
                </div>
              </bk-button>
              <ul class="bk-dropdown-list" slot="dropdown-content">
                <li
                  v-for="item in operateMore"
                  :key="item.id"
                  v-test="item.id"
                  v-bk-tooltips="{
                    content: item.tips,
                    disabled: !item.tips,
                    placements: ['left'],
                    width: 300,
                    boundary: 'window'
                  }">
                  <a href="javascript:;" @click="handleOperate(item.id)">{{ item.name }}</a>
                </li>
              </ul>
            </bk-dropdown-menu>
          </div>
        </template>
      </auth-component>
      <CopyDropdown
        class="ml10"
        :disabled="!total"
        :not-selected="selectionCount"
        :get-ips="handleCopyIp" />
      <!-- 权限中心： 仅返回可查看业务列表，同时附带操作权限 -->
      <!-- <bk-biz-select
        v-model="biz"
        class="ml10 select-biz"
        action="plugin_instance_view"
        :auto-request="autoRequest"
        :placeholder="$t('全部业务')"
        @change="handleBizChange">
      </bk-biz-select> -->
    </div>
    <!--搜索-->
    <div class="list-operate-right ml10">
      <bk-search-select
        ref="searchSelect"
        v-test="'searchSelect'"
        ext-cls="right-select"
        :data="filterSearchSelectData"
        v-model="searchSelectValue"
        :show-condition="false"
        :placeholder="$t('搜索IP管控区域操作系统Agent状态')"
        @paste.native.capture.prevent="handlePaste"
        @change="handleValueChange">
      </bk-search-select>
    </div>
  </section>
</template>
<script lang="ts">
import { Component, Prop, Ref, Mixins, Emit, Watch, Model } from 'vue-property-decorator';
import { IPluginList, ICondition, IMenu } from '@/types/plugin/plugin-type';
import { IBkBiz, ISearchItem } from '@/types';
import { searchSelectPaste } from '@/common/util';
import HeaderFilterMixins from '@/components/common/header-filter-mixins';
import { MainStore, PluginStore } from '@/store/index';
import PluginList from './plugin-list.vue';
import CopyDropdown from '@/components/common/copy-dropdown.vue';

@Component({
  name: 'plugin-list-operate',
  components: { CopyDropdown },
})
export default class PluginListOperate extends Mixins(HeaderFilterMixins) {
  @Model('change', { type: Array, default: () => ([]) }) private searchValues!: ISearchItem[]; // 其它筛选

  @Prop({ default: () => ([]), type: Array }) private readonly searchSelectData!: ISearchItem[];
  @Prop({ default: 'current', type: String }) private readonly checkType!: 'current' | 'all';
  @Prop({ default: 0, type: Number }) private readonly runningCount!: number;
  @Prop({ default: () => [], type: Array }) private readonly selections!: IPluginList[];
  @Prop({ default: () => [], type: Array }) private readonly excludeData!: IPluginList[];
  @Prop({ default: () => [], type: Array }) private readonly operateMore!: IMenu[];
  @Prop({ default: 0, type: Number }) private readonly total!: number;

  @Ref('searchSelect') private readonly searchSelect: any;
  @Ref('tree') private readonly tree: any;

  private topoLoading = false;
  private moreDropdownShow = false;
  private topoFliterTimer: any = null;
  private topoFliterValue = '';
  private biz: number[] = [];
  public searchSelectValue: ISearchItem[] = this.searchValues;

  private get selectionCount() {
    if (this.checkType === 'current') {
      return !this.selections.length;
    }
    return !this.runningCount || !(this.runningCount - this.excludeData.length);
  }

  private get filterSearchSelectData() { // search select数据源
    const ids = this.searchSelectValue.map(item => item.id);
    return this.filterData.filter(item => !ids.includes(item.id));
  }
  private get selectedBiz() {
    return MainStore.selectedBiz;
  }
  // private get autoRequest() {
  //   return !MainStore.permissionSwitch;
  // }
  private get viewBizList() { // 同 PluginStore.authorityMap.view_action, 否则就是后端有bug
    return MainStore.bkBizList.filter(item => item.has_permission);
  }
  // 可操作的权限列表
  private get operateBizIds(): number[] {
    return PluginStore.authorityMap.operate_action || [];
  }

  // 找出没有操作权限的业务
  private get notOperatePermissonBiz(): IBkBiz[] {
    // 实际生效的查看业务
    const actualViewBiz = this.selectedBiz.length
      ? this.viewBizList.filter(item => this.selectedBiz.includes(item.bk_biz_id))
      : this.viewBizList;
    // 返回 实际生效的查看业务 与 可操作的业务列表 的差值
    return actualViewBiz.filter(item => !this.operateBizIds.includes(item.bk_biz_id));
  }
  private get applyInfo() {
    return this.notOperatePermissonBiz.map(item => ({
      action: 'plugin_operate',
      instance_id: item.bk_biz_id,
      instance_name: item.bk_biz_name,
    }));
  }

  // @Watch('selectedBiz')
  // public handleBizSelect() {
  //   this.handleBizChange();
  // }
  @Watch('searchSelectData')
  public handleSearchSelectDataChange(data: ISearchItem[]) {
    this.filterData = JSON.parse(JSON.stringify(data));
  }

  @Watch('searchValues', { deep: true })
  public handleSearchValuesChange(v: ISearchItem[]) {
    this.searchSelectValue = JSON.parse(JSON.stringify(v));
  }


  public handlePaste(e: any): void {
    searchSelectPaste({
      e,
      selectedValue: this.searchSelectValue,
      filterData: this.filterData,
      selectRef: this.searchSelect,
      pushFn: this.handlePushValue,
      changeFn: this.handleValueChange,
      areaFilter: true,
    });
  }

  @Emit('plugin-operate')
  public handleOperate(operate: string) {
    return operate;
  }

  @Emit('filter-change')
  public handleValueChange() {
    return { type: 'search',  value: JSON.parse(JSON.stringify(this.searchSelectValue)) };
  }

  private async handleCopyIp(type: string) {
    const isIPv4 = !this.$DHCP || !type.includes('v6');
    const ipKey = isIPv4 ? 'inner_ip' : 'inner_ipv6';
    const associateCloud = type.includes('cloud');
    const rows = this.selections.filter(item => item[ipKey]);
    console.log(ipKey);
    let list = associateCloud
      ? rows.map(item => (isIPv4 ? `${item.bk_cloud_id}:${item[ipKey]}` : `${item.bk_cloud_id}:[${item[ipKey]}]`))
      : rows.map(item => item[ipKey]);
    const isAll = type.includes('all');
    const isSelectedAllPages = this.checkType !== 'current';
    if (isAll || isSelectedAllPages) {
      const params: {
        pagesize: number
        conditions: ICondition[]
        'exclude_hosts'?: number[]
        'only_ip': boolean
        'bk_biz_id'?: number[]
        'return_field': string
        'cloud_id_ip'?: { [key: string]: boolean }
      } = {
        pagesize: -1,
        conditions: (this.$parent as PluginList).getConditions(!isAll ? 'operate' : 'load'),
        only_ip: true,
        return_field: ipKey,
      };
      if (associateCloud) {
        params.cloud_id_ip = {
          [ipKey.includes('v6') ? 'ipv6' : 'ipv4']: true,
        };
      }
      if (!isAll && this.excludeData.length) {
        params.exclude_hosts = this.excludeData.map(item => item.bk_host_id);
      }
      if (this.selectedBiz?.length) {
        params.bk_biz_id = this.selectedBiz;
      }
      const data = await PluginStore.getHostList(params);
      list = data.list;
    }
    return Promise.resolve(list);
  }

  private async handleSelectRemote(keyword: string) {
    this.tree && this.tree.filter(keyword);
  }

  private handleValuesChange(options: IMenu) {
    this.tree && this.tree.setChecked(options.id, { emitEvent: true, checked: false });
  }

  private getShowCheckbox(node: Dictionary) {
    return node.type !== 'plugin';
  }
}
</script>
<style lang="postcss" scoped>
.dropdown-btn {
  >>> .bk-button-loading {
    /* stylelint-disable-next-line declaration-no-important */
    background-color: unset !important;
    * {
      /* stylelint-disable-next-line declaration-no-important */
      background-color: #63656e !important;
    }
  }
}
.list-operate {
  display: flex;
  justify-content: space-between;
  &-left {
    display: flex;
    .dropdown-trigger-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      color: #63656e;
      font-size: 14px;
      .icon-angle-down {
        font-size: 22px;
      }
    }
    .bk-dropdown-list {
      li {
        cursor: pointer;
        font-size: 14px;
      }
    }
    .plugin-deploy-btn {
      min-width: 88px;
    }
    .select-biz {
      background: #fff;
      max-width: 240px;
    }
    .select-wrapper {
      position: relative;
      width: 240px;
    }
  }
  &-right {
    flex-basis: 350px;
    .right-select {
      background: #fff;
    }
  }
}
</style>
