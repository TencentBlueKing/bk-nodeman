<template>
  <div class="gse-config-wrapper" v-bkloading="{ isLoading: loading }" v-test="'configWrapper'">
    <Tips :list="tipsList" class="mb20"></Tips>
    <auth-component
      class="mb14"
      tag="div"
      :authorized="apCreatePermission"
      :apply-info="[{ action: 'ap_create' }]">
      <template slot-scope="{ disabled }">
        <bk-button
          v-test="'addAp'"
          class="w100"
          theme="primary"
          :disabled="disabled"
          @click.stop="operaHandler($event, 'add')">
          {{ $t('新建') }}
        </bk-button>
      </template>
    </auth-component>
    <section class="access-point-collapse">
      <template v-for="accessPoint in accessPointList">
        <RightPanel
          class="access-point-item"
          :align-center="false"
          :key="accessPoint.id"
          collapse-color="#313238"
          title-bg-color="#FAFBFD"
          :collapse.sync="accessPoint.collapse">
          <div class="collapse-header" slot="title">
            <div class="access-point-status">
              <div class="col-status" v-if="accessPoint.status">
                <span :class="`status-mark status-${ accessPoint.status.toLocaleLowerCase() }`"></span>
              </div>
              <div class="col-status" v-else>
                <span class="status-mark status-unknown"></span>
              </div>
            </div>
            <div class="header-title">
              <div class="block-flex">
                <h3 class="access-point-title">
                  {{ accessPoint.name }}
                </h3>
                <span class="title-tag" v-if="accessPoint.ap_type === 'system'">{{ $t('默认') }}</span>
                <auth-component
                  tag="div"
                  :authorized="accessPoint.edit"
                  :apply-info="[{
                    action: 'ap_edit',
                    instance_id: accessPoint.id,
                    instance_name: accessPoint.name
                  }]">
                  <template slot-scope="{ disabled }">
                    <bk-button
                      v-test="'editAp'"
                      ext-cls="access-point-operation"
                      text
                      :disabled="disabled"
                      @click.stop="operaHandler(accessPoint, 'edit')">
                      <i class="nodeman-icon nc-icon-edit-2"></i>
                    </bk-button>
                  </template>
                </auth-component>
                <auth-component
                  tag="div"
                  :authorized="accessPoint.delete"
                  :apply-info="[{
                    action: 'ap_delete',
                    instance_id: accessPoint.id,
                    instance_name: accessPoint.name
                  }]">
                  <template slot-scope="{ disabled }">
                    <bk-popover placement="top" :disabled="!accessPoint.is_used">
                      <bk-button
                        ext-cls="access-point-operation"
                        v-if="accessPoint.ap_type !== 'system'"
                        v-test="'deleteAp'"
                        text
                        :disabled="disabled || accessPoint.is_used"
                        @click.stop="operaHandler(accessPoint, 'delete')">
                        <i class="nodeman-icon nc-delete-2"></i>
                      </bk-button>
                      <div slot="content">{{ $t('该接入点被使用中无法删除') }}</div>
                    </bk-popover>
                  </template>
                </auth-component>
              </div>
              <p class="access-point-remarks" v-if="accessPoint.description">
                <span>ID:</span>
                <span class="point-id">{{ accessPoint.id | filterEmpty }}</span>
                <span class="point-desc" v-if="accessPoint.description">{{ accessPoint.description }}</span>
              </p>
            </div>
          </div>
          <div class="collapse-container" slot>
            <AccessPointTable
              v-if="accessPoint.view"
              class="access-point-table"
              :access-point="accessPoint">
            </AccessPointTable>
            <exception-card
              v-else
              type="notPower"
              :has-border="false"
              @click="handleApplyPermission(accessPoint)">
            </exception-card>
          </div>
        </RightPanel>
      </template>
    </section>
  </div>
</template>

<script lang="ts">
import { Vue, Component } from 'vue-property-decorator';
import { MainStore, ConfigStore } from '@/store/index';
import { IApExpand } from '@/types/config/config';
import { RawLocation } from 'vue-router';
import { bus } from '@/common/bus';
import RightPanel from '@/components/common/right-panel.vue';
import AccessPointTable from './access-point-table.vue';
import Tips from '@/components/common/tips.vue';
import ExceptionCard from '@/components/exception/exception-card.vue';

@Component({
  name: 'GseConfig',
  components: {
    RightPanel,
    AccessPointTable,
    Tips,
    ExceptionCard,
  },
})
export default class GseConfig extends Vue {
  private loading = true;
  private tipsList = [
    this.$t('gseTopTips1'),
    this.$t('gseTopTips2'),
  ];
  private accessPointList: IApExpand[] = [];
  private apCreatePermission = false;

  private get permissionSwitch() {
    return MainStore.permissionSwitch;
  }

  private mounted() {
    if (this.permissionSwitch) {
      this.getCreatePermission();
    }
    this.getAccessPointList();
  }
  private async getAccessPointList() {
    this.loading = true;
    const data = await ConfigStore.requestAccessPointList();
    data.forEach((point) => {
      point.is_used = true;
      point.proxy_package = point.proxy_package || [];
    });
    const statusList = await ConfigStore.requestAccessPointIsUsing();
    if (statusList.length) {
      data.forEach((point) => {
        point.is_used = point.is_default || statusList.some(id => id === point.id);
      });
    }
    this.loading = false;
    this.accessPointList.splice(0, this.accessPointList.length, ...data);
  }
  private operaHandler(data: IApExpand, type: string) {
    if (type === 'delete') {
      this.$bkInfo({
        type: 'warning',
        title: this.$t('确认删除此接入点'),
        confirmFn: async (vm: any) => {
          vm.close();
          this.loading = true;
          const res = await ConfigStore.requestDeletetPoint({ pointId: data.id as number });
          if (!!res && res.result) {
            const index = this.accessPointList.findIndex(item => item.id === data.id);
            this.accessPointList.splice(index, 1);
            this.$bkMessage({
              theme: 'success',
              message: this.$t('删除接入点成功'),
            });
          }
          this.loading = false;
        },
      });
    } else {
      const route: RawLocation = {
        name: 'accessPoint',
      };
      if (type !== 'add') {
        route.params = {
          pointId: `${data.id}`,
        };
      }
      this.$router.push(route);
    }
  }
  private async getCreatePermission() {
    const res = await ConfigStore.getApPermission();
    this.apCreatePermission = res.create_action;
  }
  private handleApplyPermission(accessPoint: IApExpand) {
    bus.$emit('show-permission-modal', {
      params: {
        apply_info: [{
          action: 'ap_view',
          instance_id: accessPoint.id,
          instance_name: accessPoint.name,
        }],
      },
    });
  }
}
</script>

<style lang="postcss" scoped>
.mb14 {
  margin-bottom: 14px;
}
.w100 {
  width: 100px;
}
.gse-config-wrapper {
  padding-bottom: 20px;
  min-height: calc(100vh - 142px);
  overflow: auto;
  .gse-config-container {
    margin-top: 24px;
  }
  .access-point-collapse {
    /deep/ .right-panel-title {
      padding-right: 14px;
      border: 1px solid #dcdee5;
      border-bottom: 0;
    }
    /deep/ .title-desc {
      width: 100%;
    }
  }
  .access-point-item {
    border-bottom: 1px solid #dcdee5;
    & + .access-point-item {
      margin-top: 20px;
    }
  }
  .collapse-header {
    display: flex;
    padding: 14px 0 15px 5px;
    .access-point-status {
      padding-top: 4px;
      font-size: 0;
    }
    .status-mark {
      margin-right: 0;
    }
    .status-normal {
      border-color: #e5f6ea;
      background: #3fc06d;
    }
    .status-abnormal {
      border-color: #ffe6e6;
      background: #ea3636;
    }
    .header-title {
      flex: 1;
      padding-left: 12px;
      font-size: 0;
    }
    .block-flex {
      display: flex;
      align-items: center;
    }
    .access-point-title {
      display: inline-block;
      margin: 0;
      font-size: 14px;
      color: #313238;
    }
    .title-tag {
      display: inline-block;
      margin-left: 10px;
      padding: 0 4px;
      line-height: 16px;
      border-radius: 2px;
      font-size: 12px;
      font-weight: normal;
      color: #fff;
      background: #979ba5;
    }
    .access-point-remarks {
      display: flex;
      margin-top: 6px;
      line-height: 14px;
      font-size: 12px;
      font-weight: normal;
      color: #979ba5;
    }
    .point-id {
      padding-left: 10px;
    }
    .point-desc {
      margin-left: 10px;
      padding-left: 10px;
      border-left: 1px solid #dcdee5;
    }
  }
  .access-point-operation {
    margin-left: 10px;
    height: auto;
    font-size: 14px;
    color: #979ba5;
    &:not(.is-disabled):hover {
      color: #3a84ff;
    }
  }
  .collapse-container {
    background: #fff;
  }
  >>> .access-point-table tr:last-child td {
    border-bottom: 0;
  }
}
</style>
