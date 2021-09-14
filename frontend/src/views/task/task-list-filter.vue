<template>
  <div class="task-filter">
    <section class="task-filter-cantaier mt20">
      <div class="task-filter-left mr20">
        <!--选择业务-->
        <bk-biz-select
          v-model="biz"
          ext-cls="left-select"
          :placeholder="$t('全部业务')"
          @change="handleBizChange">
        </bk-biz-select>
        <div class="filter-check ml20">
          <bk-checkbox
            v-test="'toggleDeploy'"
            :value="hideAutoDeploy"
            @change="handleCheckChange">
            {{ $t('隐藏自动部署任务') }}
          </bk-checkbox>
        </div>
      </div>
      <div class="task-filter-right">
        <bk-date-picker
          v-test="'datePicker'"
          ext-cls="ml10 right-picker"
          :clearable="false"
          :shortcuts="shortcuts"
          :type="'datetimerange'"
          :shortcut-close="true"
          :use-shortcut-text="true"
          :shortcut-selected-index="3"
          :value="dateTimeRange"
          :placeholder="$t('选择日期范围')"
          @change="handlePickerChange"
          @shortcut-change="handleShortcutChange">
        </bk-date-picker>
        <bk-search-select
          class="ml10 right-select"
          v-test="'searchSelect'"
          ref="searchSelectRef"
          :show-condition="false"
          :placeholder="$t('搜索任务ID、执行者、任务类型、操作类型、部署策略、执行状态')"
          :data="searchSelectData"
          v-model="searchSelectValue"
          @change="handleSearchSelectChange">
        </bk-search-select>
      </div>
    </section>
  </div>
</template>

<script lang="ts">
import { Vue, Component, Prop, Emit, Ref } from 'vue-property-decorator';
import { ISearchItem } from '@/types';
import { deepClone } from '@/common/util';
import { MainStore } from '@/store';

@Component({
  name: 'task-list-filter',
})
export default class PluginRule extends Vue {
  @Prop({ default: true, type: Boolean }) private readonly hideAutoDeploy!: boolean;
  @Prop({ default: () => ([]), type: Array }) private readonly searchSelectValue!: ISearchItem[];
  @Prop({ type: Array, default: () => ([]) }) private readonly filterData!: ISearchItem[];
  @Prop({ type: Array, default: () => {
    const end = new Date();
    const start = new Date();
    start.setTime(start.getTime() - (3600 * 1000 * 24 * 30));
    return [start, end];
  } }) private readonly dateTimeRange!: Date[];
  @Prop({ type: Array, default: () => [
    {
      text: window.i18n.t('今天'),
      value() {
        const end = new Date();
        const start = new Date();
        return [start, end];
      },
    }, {
      text: window.i18n.t('近7天'),
      value() {
        const end = new Date();
        const start = new Date();
        start.setTime(start.getTime() - (3600 * 1000 * 24 * 7));
        return [start, end];
      },
    }, {
      text: window.i18n.t('近15天'),
      value() {
        const end = new Date();
        const start = new Date();
        start.setTime(start.getTime() - (3600 * 1000 * 24 * 15));
        return [start, end];
      },
    }, {
      text: window.i18n.t('近30天'),
      value() {
        const end = new Date();
        const start = new Date();
        start.setTime(start.getTime() - (3600 * 1000 * 24 * 30));
        return [start, end];
      },
    },
    {
      text: window.i18n.t('近1年'),
      value() {
        const end = new Date();
        const start = new Date();
        start.setTime(start.getTime() - (3600 * 1000 * 24 * 365));
        return [start, end];
      },
    },
  ] }) private readonly shortcuts!: { text: string, value: Function }[];

  @Ref('searchSelectRef') private readonly searchSelectRef!: any;

  private biz: Array<string|number> = MainStore.selectedBiz;

  // search select数据源
  private get searchSelectData() {
    const ids = this.searchSelectValue.map(item => item.id);
    return this.filterData.filter(item => !ids.includes(item.id));
  }

  @Emit('search-change')
  public handleSearchSelectChange(list: ISearchItem[]) {
    const copyList: ISearchItem[] = deepClone([...list]);
    copyList.forEach((item) => {
      if (item.values) {
        item.values.forEach((option) => {
          option.checked = true;
        });
      }
    });
    return copyList;
  }
  // 切换业务 biz
  @Emit('biz-change')
  public handleBizChange() {
    return this.biz;
  }
  // 切换隐藏自动部署
  @Emit('deploy-change')
  public handleCheckChange(value: boolean) {
    return value;
  }

  // picker变更
  @Emit('picker-change')
  public pickerChange(param: { type: string, value: string | Dictionary | Date[] }) {
    return param;
  }

  private handlePickerChange(date: Date[], type?: string) { // type - date | time
    if (type) {
      this.pickerChange({ type: 'date', value: date });
      this.pickerChange({ type: 'dateType', value: 'date' });
    }
  }
  private handleShortcutChange(value: Dictionary) {
    if (value) {
      this.pickerChange({ type: 'dateType', value });
    }
  }
}
</script>

<style lang="postcss" scoped>

.task-filter {
  .task-filter-cantaier {
    display: flex;
    justify-content: space-between;
  }
  .task-filter-left {
    display: flex;
    align-items: center;
  }
  .left-select {
    width: 160px;
    background: #fff;
  }
  >>> .bk-form-checkbox:not(.is-checked) .bk-checkbox {
    background: #fff;
  }
  .task-filter-right {
    display: flex;
    flex: 1;
    max-width: 780px;
    .right-picker {
      width: 280px;
    }
    .right-select {
      flex: 1;
      background: #fff;
    }
  }
}
</style>
