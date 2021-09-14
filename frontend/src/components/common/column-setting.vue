<template>
  <bk-popover
    class="popover"
    theme="light table-setting"
    trigger="click"
    placement="bottom-end"
    :on-hide="handleOnHide"
    ref="popover">
    <span v-bk-tooltips.top="$t('表格展示设置')" class="col-setting" v-test.common="'headSet'">
      <i class="bk-icon icon-cog-shape"></i>
    </span>
    <template #content>
      <div class="set-filter" ref="filterPanel" v-test.common="'headSetPanel'">
        <div class="set-filter-title">{{ $t('表格设置') }}</div>
        <ul class="set-filter-list" v-if="filterHead">
          <li class="list-item">
            {{ $t('字段显示设置') }}
            <!-- <span class="list-item-tips">{{ $t('最多选8项') }}</span> -->
          </li>
          <li class="list-item">
            <bk-checkbox :value="isAllChecked" @change="handleCheckedAll">{{ $t('全选') }}</bk-checkbox>
          </li>
          <li v-for="item in filter" :key="item.id" class="list-item">
            <bk-checkbox
              :value="item.checked"
              :disabled="item.disabled"
              @change="handleCheckedChange($event, item)">
              {{ item.name }}
            </bk-checkbox>
          </li>
        </ul>
        <section class="set-font mb30" v-if="fontSetting">
          <div class="set-font-title">
            {{ $t('字号设置') }}
          </div>
          <div class="bk-button-group">
            <bk-button
              v-for="config in fontConfig"
              :key="config.id"
              :class="{ 'is-selected': config.checked }"
              @click="fontSetHandle(config)">{{ config.name }}</bk-button>
          </div>
        </section>
        <div class="set-filter-footer">
          <bk-button theme="primary" class="footer-btn" @click="handleFilterConfirm">{{ $t('确认') }}</bk-button>
          <bk-button class="ml10" @click="handleFilterCancel">{{ $t('取消') }}</bk-button>
        </div>
      </div>
    </template>
  </bk-popover>
</template>
<script lang="ts">
import { Component, Vue, Prop, Ref, Emit, Watch } from 'vue-property-decorator';
import { MainStore } from '@/store/index';
import { bus } from '@/common/bus';
import { STORAGE_KEY_COL, STORAGE_KEY_FONT } from '@/config/storage-key';
import { ICheckItem, ITabelFliter } from '@/types';

@Component({ name: 'column-setting' })

export default class ColumnSetting extends Vue {
  // 不同表格的区分
  @Prop({ type: String, default: '' }) private readonly localMark!: string;
  @Prop({ type: [Object, Array], default: () => ({}) }) private readonly value!: { [key: string]: ITabelFliter };
  @Prop({ type: Boolean, default: false }) private readonly filterHead!: boolean;
  @Prop({ type: Boolean, default: true }) private readonly fontSetting!: boolean;
  @Ref('popover') private readonly popover!: any;

  private filter: { [key: string]: ITabelFliter } = JSON.parse(JSON.stringify(this.value));
  private fontConfig: ICheckItem[] = [];

  private get fontList() {
    return MainStore.fontList;
  }
  // 是否勾选所有项
  private get isAllChecked() {
    return Object.keys(this.filter).every((key) => {
      const item = this.filter[key];
      return item.disabled || (!item.disabled && item.checked);
    });
  }

  @Watch('value', { deep: true })
  public handleValueChange() {
    this.filter = JSON.parse(JSON.stringify(this.value));
  }
  @Watch('fontList', { deep: true })
  public handleFontListChange() {
    this.fontConfig = JSON.parse(JSON.stringify(this.fontList));
  }

  private created() {
    bus.$on('toggleSetting', this.togglePopover);
    this.fontConfig = JSON.parse(JSON.stringify(this.fontList));
  }
  private mounted() {
    if (this.localMark) {
      this.initColConfig();
    }
  }
  private beforDistory() {
    bus.$off('toggleSetting', this.togglePopover);
  }

  /**
   * 全选事件
   * @param {Boolean} v
   */
  private handleCheckedAll(v: boolean) {
    Object.keys(this.filter).forEach((key) => {
      if (!this.filter[key].disabled) {
        this.filter[key].checked = v;
      }
    });
  }
  /**
   * 表头列勾选事件
   * @param {Boolean} v
   * @param {Object} item
   */
  private handleCheckedChange(v: boolean, item: ITabelFliter) {
    if (item) {
      item.checked = v;
    }
  }
  /**
   * 设置表格字体大小
   */
  private fontSetHandle(config: { id: string }) {
    this.fontConfig.forEach((item) => {
      item.checked = config.id === item.id;
    });
  }
  /**
   * 确定
   */
  @Emit('update')
  private handleFilterConfirm() {
    Object.keys(this.filter).forEach((key) => {
      this.filter[key].mockChecked = this.filter[key].checked;
    });
    const data = Object.keys(this.filter).reduce((obj: { [key: string]: boolean }, next) => {
      obj[next] = !!this.filter[next].mockChecked;
      return obj;
    }, {});
    MainStore.setFont(this.fontConfig);
    const currFont = this.fontConfig.find(item => item.checked);
    this.handleSetStorage(data, currFont ? `${currFont.id}` : '');
    this.popover && this.popover.instance.hide();
    return this.filter;
  }
  /**
   * 取消
   */
  @Emit('cancel')
  private handleFilterCancel() {
    this.popover && this.popover.instance.hide();
    return this.filter;
  }
  /**
   * 设置存储信息
   */
  private handleSetStorage(data: { [key: string]: boolean }, font: string) {
    try {
      window.localStorage.setItem(this.localMark + STORAGE_KEY_COL, JSON.stringify(data));
      window.localStorage.setItem(STORAGE_KEY_FONT, font);
    } catch (_) {
      this.$bkMessage({
        theme: 'error',
        message: this.$t('浏览器不支持本地存储'),
      });
    }
  }
  /**
   * 弹窗显示
   */
  private handleOnHide() {
    window.setTimeout(() => {
      this.filter = JSON.parse(JSON.stringify(this.value));
      this.fontConfig = JSON.parse(JSON.stringify(this.fontList));
    }, 500);
  }
  private togglePopover(isShow: boolean) {
    if (this.popover) {
      if (isShow) {
        this.popover.instance.show();
      } else {
        this.handleFilterCancel();
      }
    }
  }
  private initColConfig() {
    const data = this.handleGetStorage();
    if (data && Object.keys(data).length) {
      Object.keys(this.filter).forEach((key) => {
        this.filter[key].mockChecked = !!data[key];
        this.filter[key].checked = !!data[key];
      });
    }
    this.$emit('update', this.filter);
  }
  /**
   * 获取存储信息
   */
  private handleGetStorage() {
    let data: { [key: string]: boolean } = {};
    try {
      data = JSON.parse(window.localStorage.getItem(this.localMark + STORAGE_KEY_COL) || '');
    } catch (_) {
      data = {};
    }
    return data;
  }
}
</script>
<style lang="postcss" scoped>
@import "@/css/mixins/nodeman.css";

.popover {
  cursor: pointer;

  @mixin layout-flex row, center, center;
}
</style>
