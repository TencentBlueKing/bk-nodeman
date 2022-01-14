/**
* Tencent is pleased to support the open source community by making 蓝鲸智云PaaS平台社区版 (BlueKing PaaS Community
* Edition) available.
* Copyright (C) 2017-2020 THL A29 Limited, a Tencent company. All rights reserved.
* Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
* You may obtain a copy of the License at
* https://opensource.org/licenses/MIT
* Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
* an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
* specific language governing permissions and limitations under the License.
*/
<template>
  <bk-dialog
    width="768"
    ext-cls="permission-dialog"
    :z-index="2010"
    :draggable="false"
    :mask-close="false"
    :header-position="'left'"
    :title="''"
    :value="isModalShow"
    @cancel="onCloseDialog"
    @after-leave="handleDialogLeave">
    <div class="permission-modal" v-bkloading="{ isLoading: loading, opacity: 1 }">
      <div class="permission-header">
        <span class="title-icon">
          <img :src="lock" alt="permission-lock" class="lock-img" />
        </span>
        <h3>{{ $t('该操作需要以下权限') }}</h3>
      </div>
      <table class="permission-table table-header">
        <thead>
          <tr>
            <th width="20%">{{ $t('系统') }}</th>
            <th width="30%">{{ $t('需要申请的权限') }}</th>
            <th width="50%">{{ $t('关联的资源实例') }}</th>
          </tr>
        </thead>
      </table>
      <div class="table-content">
        <table class="permission-table">
          <tbody>
            <template v-if="actionsList.length > 0">
              <tr v-for="(action, index) in actionsList" :key="index">
                <td width="20%">{{ (isCompatibleRes ? action.systemName : action.system) | filterEmpty }}</td>
                <td width="30%">{{ (isCompatibleRes ? action.actionName : action.action) | filterEmpty }}</td>
                <td width="50%" v-if="!isCompatibleRes">{{ action.instance_name | filterEmpty }}</td>
                <td width="50%" v-else>
                  <p
                    class="resource-type-item"
                    v-for="(reItem, reIndex) in getResource(action.related_resource_types)"
                    :key="reIndex">
                    {{reItem}}
                  </p>
                </td>
              </tr>
            </template>
            <tr v-else>
              <td class="no-data" colspan="3">{{ $t('无数据') }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div class="permission-footer" slot="footer">
      <div class="button-group">
        <bk-button
          theme="primary"
          :disabled="!url || !actionsList.length"
          :loading="loading"
          @click="goToApply">
          {{ $t('去申请') }}
        </bk-button>
        <bk-button theme="default" @click="onCloseDialog">{{ $t('取消') }}</bk-button>
      </div>
    </div>
  </bk-dialog>
</template>
<script lang="ts">
import { Vue, Component } from 'vue-property-decorator';
import { MainStore } from '@/store/index';
import lockSvg from '@/images/lock-radius.svg';
import { IAuthApply } from '@/types';

interface ITrigger {
  trigger: 'click' | 'request'
  params?: IAuthApply
  questRes: any
}

@Component({ name: 'permissionModal' })

export default class PermissionModal extends Vue {
  private url = '';
  private isModalShow = false;
  private actionsList: {
    system?: string
    action?: string
    'instance_name'?: string
    related_resource_types?: any[]
  }[] = [];
  private loading = false;
  private lock = lockSvg;

  private get isCompatibleRes() {
    return !!this.actionsList.find(item => !!item.related_resource_types);
  }

  private async loadPermissionUrl(params: IAuthApply) {
    this.loading = true;
    // 资源池业务是 针对超级管理员的业务
    params.apply_info = params.apply_info.filter((item: Dictionary) => item.instance_name !== this.$t('资源池'));
    const res = await MainStore.getApplyPermission(params);
    this.url = res.url;
    this.actionsList = res.apply_info;
    this.loading = false;
  }
  private show({ trigger = 'click', params, questRes }: ITrigger) {
    this.isModalShow = true;
    if (trigger === 'click') {
      this.loadPermissionUrl(params as IAuthApply);
    } else if (trigger === 'request') {
      this.formatData(questRes);
    }
  }
  private formatData(res: any) {
    const { apply_data: applyData, apply_url: applyUrl, permission } = res;
    const data = applyData || permission;
    const { actions = [], system_name: systemName = '' } = data;
    this.actionsList = actions.map(action => ({
      actionName: action.name,
      systemName,
      related_resource_types: action.related_resource_types,
    }));
    this.url = applyUrl;
  }
  public getResource(resources: any[]) {
    if (resources.length === 0) {
      return ['--'];
    }

    const data: string[] = [];
    resources.forEach((resource) => {
      if (resource.instances.length > 0) {
        const instances = resource.instances.map((instanceItem: any[]) => instanceItem.map(item => item.name || item.id).join('，')).join('，');
        const resourceItemData = `${resource.type_name}：${instances}`;
        data.push(resourceItemData);
      }
    });
    return data;
  }
  private goToApply() {
    if (this.loading) {
      return;
    }

    if (self === top) {
      window.open(this.url, '__blank');
    } else {
      try {
        window.top.BLUEKING.api.open_app_by_other('bk_iam', this.url);
      } catch (_) {
        window.open(this.url, '__blank');
      }
    }
  }
  private onCloseDialog() {
    this.isModalShow = false;
  }
  private handleDialogLeave() {
    this.actionsList.splice(0, this.actionsList.length);
    this.url = '';
  }
}
</script>
<style lang="postcss" scoped>
.permission-modal {
  .permission-header {
    text-align: center;
    .title-icon {
      display: inline-block;
    }
    .lock-img {
      width: 120px;
    }
    h3 {
      margin: 6px 0 24px;
      color: #63656e;
      font-size: 20px;
      font-weight: normal;
      line-height: 1;
    }
  }
  .permission-table {
    width: 100%;
    color: #63656e;
    border-bottom: 1px solid #e7e8ed;
    border-collapse: collapse;
    table-layout: fixed;
    th,
    td {
      padding: 12px 18px;
      font-size: 12px;
      text-align: left;
      border-bottom: 1px solid #e7e8ed;
      word-break: break-all;
    }
    th {
      color: #313238;
      background: #f5f6fa;
    }
  }
  .table-content {
    max-height: 260px;
    border-bottom: 1px solid #e7e8ed;
    border-top: 0;
    overflow: auto;
    .permission-table {
      border-top: 0;
      border-bottom: 0;
      td:last-child {
        border-right: 0;
      }
      tr:last-child td {
        border-bottom: 0;
      }
      .resource-type-item {
        padding: 0;
        margin: 0;
      }
    }
    .no-data {
      /* padding: 30px; */
      text-align: center;
      color: #999;
    }
  }
}
.button-group {
  .bk-button {
    margin-left: 7px;
  }
}
</style>
