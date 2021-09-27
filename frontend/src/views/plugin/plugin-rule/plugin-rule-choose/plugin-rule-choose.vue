<template>
  <bk-form v-test.policy="'chooseForm'" ref="form" class="pb10" v-bkloading="{ isLoading }">
    <bk-form-item
      :label="$t('插件功能')"
      error-display-type="normal"
      required>
      <bk-select
        class="select"
        searchable
        :clearable="false"
        v-model="pluginId"
        @selected="handlePluginChange">
        <bk-option
          v-for="option in pluginList"
          :key="option.id"
          :id="option.id"
          :name="option.label">
        </bk-option>
      </bk-select>
    </bk-form-item>
    <bk-form-item :label="$t('部署策略')" required>
      <RuleType
        :disabled-old-rule="tableData.length === 0"
        v-model="ruleType">
      </RuleType>
    </bk-form-item>
    <bk-form-item
      :label="$t('选择策略')"
      :label-width="labelWidth"
      required
      v-show="ruleType === 'oldRule' && tableData.length > 0">
      <RuleTable
        :table-data="tableData"
        :pagination="pagination"
        :choose-id="chooseId"
        @rule-choose="handleRuleChoose">
      </RuleTable>
    </bk-form-item>
    <bk-form-item>
      <bk-button v-test.common="'formCommit'"
                 class="nodeman-primary-btn" theme="primary" :disabled="btnNextDisabled" @click="handleCreateRule">
        {{ btnText }}
      </bk-button>
      <bk-button class="ml5 nodeman-cancel-btn" @click="routerBack">
        {{ $t('取消') }}
      </bk-button>
    </bk-form-item>
  </bk-form>
</template>
<script lang="ts">
import { Component, Mixins, Ref, Prop } from 'vue-property-decorator';
import { PluginStore } from '@/store';
import FormLabelMixin from '@/common/form-label-mixin';
import routerBackMixin from '@/common/router-back-mixin';
import RuleType from './rule-type.vue';
import RuleTable from './rule-table.vue';
import { IPagination } from '@/types';
import { IChoosePlugin, IPolicyBase } from '@/types/plugin/plugin-type';
import { sort } from '@/common/util';

@Component({
  name: 'rule-add',
  components: {
    RuleType,
    RuleTable,
  },
})
export default class RuleAdd extends Mixins(FormLabelMixin, routerBackMixin) {
  @Prop({ default: '', type: [Number, String] }) private readonly defaultPluginId!: string | number;

  @Ref('form') private readonly form!: Vue;

  private isLoading = false;
  private ruleType: 'oldRule' | 'newRule' = 'newRule';
  private labelWidth = 100;
  private pluginId = this.defaultPluginId;
  private pluginName = '';
  private filterName = '';
  private chooseId: number | string = '';
  private pluginList: IChoosePlugin[] = [];
  private tableData: IPolicyBase[] = [];
  private pagination: IPagination = {
    current: 1,
    count: 0,
    limit: 20,
  };

  private get btnText() {
    const textMap = {
      oldRule: this.$t('去调整目标'),
      newRule: this.$t('去新建策略'),
    };
    return textMap[this.ruleType];
  }
  private get btnNextDisabled() {
    if (this.ruleType === 'oldRule') {
      return !this.tableData.length || !this.chooseId;
    }
    return !this.pluginId;
  }

  private mounted() {
    this.minWidth = 64;
    this.labelWidth = this.initLabelWidth(this.form) || 100;
    this.getPluginList();
  }

  public handleTypeChange(active: 'oldRule' | 'newRule') {
    this.ruleType = active;
  }

  public handleCreateRule() {
    const params: Dictionary = {
      type: 'edit',
      pluginId: this.pluginId,
    };
    if (this.ruleType === 'oldRule') {
      params.id = this.chooseId;
    } else {
      params.pluginName = this.pluginName;
      params.type = 'create';
    }
    this.$router.push({
      name: 'createRule',
      params,
    });
  }

  public async handlePluginChange(newValue: number | string) {
    this.chooseId = '';
    const item = this.pluginList.find(item => item.id === newValue);
    this.pluginName = item ? item.name : '';
    if (newValue) {
      await this.getPluginStrategy();
    } else {
      this.tableData = [];
      this.ruleType = 'newRule';
    }
  }
  public async getPluginList() {
    this.isLoading = true;
    const res = await PluginStore.pluginPkgList({ simple_all: true });
    const list = res.list.filter(item => item.is_ready).map(item => ({
      label: `${item.name}(${item.description})`,
      ...item,
    }));
    sort(list, 'name');
    this.pluginList = list;
    // 初始化默认值
    if (!this.pluginId && this.pluginList[0]) {
      this.pluginId = this.pluginList[0].id;
      this.pluginName = this.pluginList[0].name;
    }
    await this.handlePluginChange(this.pluginId);
    this.isLoading = false;
  }
  public async getPluginStrategy() {
    this.isLoading = true;
    const params = this.getParams();
    const { total, list } = await PluginStore.getPluginRules(params);
    if (!this.chooseId && list.length) {
      const ableActive = list.find(item => item.permissions && item.permissions.edit);
      if (ableActive) {
        this.chooseId = ableActive.id;
      }
    }
    this.tableData = list;
    this.pagination.count = total;
    this.ruleType = !this.tableData.length ? 'newRule' : 'oldRule';
    this.isLoading = false;
  }
  public handleRuleChoose(id: number) {
    this.chooseId = id;
  }
  // 拉取策略参数
  public getParams() {
    // todo 这里没有分页要传全部页数才对
    const { pluginName, filterName, pagination } = this;
    const { current, limit } = pagination;
    const params = {
      page: current,
      pagesize: limit,
      conditions: [
        { key: 'plugin_name', value: pluginName },
      ],
    };
    if (filterName) {
      params.conditions.push({ key: 'query', value: filterName });
    }
    return params;
  }
}
</script>
<style lang="postcss" scoped>
.select {
  width: 480px;
  background: #fff;
}
</style>
