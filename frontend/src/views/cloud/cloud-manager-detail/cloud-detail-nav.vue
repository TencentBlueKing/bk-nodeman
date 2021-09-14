<template>
  <!--详情左侧面板-->
  <section class="detail-left" v-test="'cloudNav'">
    <!--搜索云区域别名-->
    <div class="detail-left-search">
      <bk-input
        v-test="'cloudFilter'"
        :placeholder="$t('搜索云区域名称')"
        right-icon="bk-icon icon-search"
        v-model="bkCloudName"
        @change="handleValueChange">
      </bk-input>
    </div>
    <!--列表-->
    <div class="detail-left-list" ref="leftList" v-bkloading="{ isLoading: loading }">
      <ul>
        <auth-component
          class="list-auth-wrapper"
          v-for="(item, index) in area.data"
          :key="index"
          tag="li"
          :title="item.bkCloudName"
          :authorized="item.view"
          :apply-info="[{
            action: 'cloud_view',
            instance_id: item.bkCloudId,
            instance_name: item.bkCloudName
          }]">
          <template slot-scope="{ disabled }">
            <div
              v-test="'cloudItem'"
              class="list-item"
              :class="{ 'is-selected': item.bkCloudId === id, 'auth-disabled': disabled }"
              @click="handleAreaChange(item)">
              <span v-bk-tooltips="{
                content: $t('存在异常Proxy'),
                placement: 'top',
                delay: [200, 0]
              }" v-if="item.exception === 'abnormal'" class="col-status">
                <span class="status-mark status-terminated"></span>
              </span>
              <span class="list-item-name">{{ item.bkCloudName }}</span>
              <span v-bk-tooltips="{
                content: $t('未安装Proxy'),
                placement: 'top',
                delay: [200, 0]
              }" v-if="!item.proxyCount" class="list-item-text error-text">
                !
              </span>
              <span v-bk-tooltips="{
                content: $t('proxy数量提示'),
                placement: 'top',
                width: 220,
                delay: [200, 0]
              }" v-if="item.proxyCount === 1" class="list-item-text warning-text">
                !
              </span>
            </div>
          </template>
        </auth-component>
      </ul>
    </div>
  </section>
</template>
<script lang="ts">
import { Component, Prop, Vue, Ref } from 'vue-property-decorator';
import { MainStore, CloudStore } from '@/store/index';
import { debounce } from '@/common/util';
import { ICloud } from '@/types/cloud/cloud';

@Component({ name: 'CloudDetailNav' })
export default class CloudDetailSide extends Vue {
  @Prop({ type: Number, default: -1 }) private readonly id!: number; // 当前选中的云区域
  @Prop({ type: Boolean, default: true }) private readonly isFirst!: boolean; // 是否是首次加载
  @Prop({ type: String, default: '' }) private readonly search!: '';

  @Ref('leftList') private readonly leftList!: any;

  private bkCloudName = this.search; // 别名
  private handleValueChange: Function = function () {}; // 别名搜索防抖
  // 区域列表
  private area: {
    list: ICloud[]
    data: ICloud[]
    isAll: boolean
    lastOffset: number
    offset: number
  } = {
    list: [],
    data: [],
    isAll: false, // 标志是否加载完毕数据
    lastOffset: -1,
    offset: 0, // 上一次滚动的位置
  };
  private loading = false;
  // 左侧列表加载状态
  private firstLoad =  this.isFirst;

  private get permissionSwitch() {
    return MainStore.permissionSwitch;
  }
  private get cloudList() {
    return CloudStore.cloudList;
  }

  private created() {
    this.handleGetCloudList();
  }
  private mounted() {
    this.handleValueChange = debounce(300, this.handleSearch);
  }

  /**
   * 搜索云区域别名
   */
  public handleSearch() {
    this.area.data = this.bkCloudName.length === 0
      ? this.area.list
      : this.area.list.filter((item) => {
        const originName = item.bkCloudName.toLocaleLowerCase();
        const currentName = this.bkCloudName.toLocaleLowerCase();
        return originName.indexOf(currentName) > -1;
      });
  }
  /**
   * 获取云区域列表
   */
  public async handleGetCloudList() {
    this.loading = true;
    const params: Dictionary = {};
    let list = [];
    if (!this.firstLoad) {
      list = this.cloudList;
    } else {
      list = await CloudStore.getCloudList(params);
    }
    this.area.list = this.permissionSwitch ? list.filter(item => item.view) : list;
    this.area.data = this.area.list;
    if (this.firstLoad) {
      this.$nextTick(() => {
        this.scrollToView();
      });
    }
    this.firstLoad = false;
    this.loading = false;
    this.handleSearch();
  }
  /**
   * 处理轮询的数据
   */
  public handleAreaChange(item: Dictionary) {
    if (this.id === item.bkCloudId) return;
    this.$router.replace({
      name: 'cloudManagerDetail',
      params: {
        id: item.bkCloudId,
        isFirst: false,
        search: this.bkCloudName,
      },
    });
  }
  /**
   * 滚动列表到可视区域
   */
  public scrollToView() {
    if (!this.leftList) return;
    const itemHeight = 42; // 每项的高度
    const offsetHeight = itemHeight * this.area.list.findIndex((item: Dictionary) => item.bkCloudId === this.id);
    if (offsetHeight > this.leftList.clientHeight) {
      this.leftList.scrollTo(0, offsetHeight - itemHeight);
    }
  }
}
</script>

<style lang="postcss" scoped>
  .detail-left {
    padding-top: 20px;
    flex: 0 0 240px;
    background-color: #fafbfd;
    &-search {
      margin-bottom: 16px;
      padding: 0 20px;
    }
    &-list {
      width: 240px;
      height: calc(100% - 55px);
      overflow-y: auto;
      .list-auth-wrapper {
        display: block;
      }
      .list-item {
        position: relative;
        display: flex;
        justify-content: space-between;
        padding-left: 40px;
        padding-right: 20px;
        line-height: 42px;
        height: 42px;
        font-size: 14px;
        cursor: pointer;
        &-name {
          flex: 1;
          max-width: 160px;
          display: inline-block;
          overflow: hidden;
          white-space: nowrap;
          text-overflow: ellipsis;
        }
        &-text {
          width: 13px;
          font-size: 14px;
          line-height: 42px;
          text-align: center;
          font-weight: 600;
        }
        .col-status {
          position: absolute;
          top: 14px;
          left: 20px;
        }
        .status-mark {
          margin-right: 0;
        }
        .error-text {
          color: #ea3636;
        }
        .warning-text {
          color: #ff9c01;
        }
        &:hover {
          background: #f0f1f5;
        }
        &.loading {
          color: #979ba5;
          .loading-name {
            font-size: 12px;
          }
        }
        &.is-selected {
          background: #e1ecff;
        }
        &.auth-disabled {
          color: #dcdee5;
          .list-item-text {
            color: #dcdee5;
          }
        }
      }
    }
  }
</style>
