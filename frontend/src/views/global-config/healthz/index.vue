<template>
  <div class="healthz-content pb30" v-bkloading="{ isLoading: nmMainLoading }">
    <HealthzServiceTable v-if="!nmMainLoading"></HealthzServiceTable>

    <section class="monitoring-category" v-for="category in monitorList" :key="category.name">
      <p class="monitoring-category-title">
        <i v-if="category.icon" :class="`monitoring-category-icon ${category.icon}`"></i>
        {{ category.name }}
      </p>
      <div class="monitoring-range">
        <section class="monitoring-range-item">
          <div class="node-list" v-if="!!category.children.length">
            <div class="node-item" v-for="(nodeName, index) in category.children" :key="index">
              <!-- :show-line="index < category.children.length - 1 && category.id !== 'saas'" -->
              <HealthzNode
                :node-name="nodeName"
                :category="category.id"
                @show-dialog="handleShowDialog">
              </HealthzNode>
            </div>
          </div>
          <ExceptionCard v-else type="notData" :has-border="false"></ExceptionCard>
        </section>
      </div>
    </section>

    <HealthzDialog
      :visible="dialogVisible"
      :mode="dialogMode"
      :dialog="dialogInfo"
      @closed="dialogVisible = false">
    </HealthzDialog>
  </div>
</template>

<script lang="ts">
import { Vue, Component } from 'vue-property-decorator';
import { ConfigStore, MainStore } from '@/store/index';
import HealthzServiceTable from './healthz-service-table.vue';
import HealthzNode from './healthz-node.vue';
import HealthzDialog from './healthz-dialog.vue';
import ExceptionCard from '@/components/exception/exception-card.vue';
// import staticData from '../healthz-copy/aaa' // 来自监控saas的接口数据

@Component({
  name: 'Healthz',
  components: {
    HealthzServiceTable,
    HealthzNode,
    HealthzDialog,
    ExceptionCard,
  },
})
export default class Healthz extends Vue {
  private dialogVisible = false;
  private dialogMode = 'saas';
  private dialogInfo: Dictionary = {};
  private monitorList: any[] = [
    {
      name: this.$t('节点管理后台服务状态'),
      id: 'backend',
      icon: 'nodeman-icon nc-backstage',
      children: [],
    },
    {
      name: this.$t('节点管理SaaS依赖周边组件状态'),
      id: 'saas',
      icon: 'nodeman-icon nc-saas',
      children: [],
    },
  ];

  private get healthzData() {
    return ConfigStore.healthzData;
  }
  private get nmMainLoading() {
    return MainStore.nmMainLoading;
  }

  private created() {
    this.getHealthz();
  }

  public async getHealthz() {
    MainStore.setNmMainLoading(true);
    // const data: any[] = staticData.map(item => ({
    //   ...item,
    //   collect_type: ConfigStore.saasDependenciesComponent.includes(item.node_name) ? 'saas' : 'backend'
    // }))

    const data: any[] = await ConfigStore.getHealthz();
    const objMap = this.classification(data, 'collect_type');
    this.monitorList.forEach((item) => {
      if (objMap[item.id]) {
        item.children = Array.from(new Set(objMap[item.id].map((node: Dictionary) => node.node_name)));
        if (item.id === 'saas') {
          ConfigStore.updateSaasComponents(item.children);
        }
      }
    });
    const tmpIPlist = Array.from(new Set(data.map((item => item.server_ip)).filter(item => !!item)));
    ConfigStore.updateSelectedIPs(tmpIPlist);
    ConfigStore.updateAllIPs(tmpIPlist);
    // 当前组件状态，-1表示初始状态，还未测试，0表示正常，1表示关注，2表示错误
    ConfigStore.updateHealthzData(data);
    MainStore.setNmMainLoading(false);
    // end

    // 仅用作数据结构分析
    Object.keys(objMap).forEach((key) => {
      const secondKey = 'node_name';
      const secondItem = this.classification(objMap[key], secondKey);
      const thirdKey = 'category';
      const thirdMap: Dictionary = {};
      Object.keys(secondItem).forEach((kk) => {
        thirdMap[`${kk}_third`] = this.classification(secondItem[kk], thirdKey);
      });
      // 第二层
      objMap[`${key}_${secondKey}_second`] = secondItem;
      // 第三层
      objMap[`${key}_${thirdKey}_third`] = thirdMap;
    });
  }
  public classification(list: any[], keyword: string) {
    const objMap: Dictionary = {};
    list.reduce((obj: Dictionary, item: any) => {
      const keyName = item[keyword] || 'other';
      if (Object.prototype.hasOwnProperty.call(obj, keyName)) {
        obj[keyName].push(item);
      } else {
        obj[keyName] = [item];
      }
      return obj;
    }, objMap);
    return objMap;
  }

  public handleShowDialog({ category, tip }: any) {
    this.dialogVisible = true;
    this.dialogInfo = tip;
    this.dialogMode = category;
  }
}
</script>

<style lang="postcss">
  .monitoring-category {
    border-radius: 2px;
    .monitoring-category-title {
      display: flex;
      align-items: center;
      margin-bottom: 16px;
      line-height: 20px;
      font-size: 14px;
      color: #313238;
    }
    .monitoring-category-icon {
      margin-right: 6px;
      font-size: 12px;
      color: #63656e;
    }
    & + .monitoring-category {
      margin-top: 40px;
    }
    .rang-item-title {
      margin-bottom: 16px;
      line-height: 16px;
      font-size: 12px;
      color: #313238;
    }
  }
  .monitoring-range {
    padding: 16px 20px 8px 20px;
    background: #fff;
    box-shadow: 0px 1px 2px 0px rgba(0, 0, 0, .1);
  }
  .monitoring-range-item {
    & + .monitoring-range-item {
      margin-top: 20px;
    }
  }
  .healthz-table {
    width: 400px;
  }
  .node-list {
    display: flex;
    flex-wrap: wrap;
    .node-item {
      margin-bottom: 16px;
    }
  }
</style>
