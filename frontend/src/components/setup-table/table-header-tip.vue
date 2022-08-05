<template>
  <section :class="['tips-content', { 'joint-tip': jointTip }]">
    <i18n tag="pre" :path="tips" v-if="tips === 'agentSetupInnerIp'">
      <span class="primary">{{ $t('「登录 IP」') }}</span>
    </i18n>
    <i18n style="line-height: 22px" tag="pre" :path="tips" v-else-if="tips === 'agentSetupPort'">
      <span class="danger">22</span>
      <span>{{ port }}</span>
      <span class="primary pointer" @mousedown.prevent @click="handleBatch">{{ $t('批量应用') }}</span>
      <p v-if="portDescription">
        <br />
        <span>{{ $t('补充说明tips', [portDescription]) }}</span>
      </p>
    </i18n>
    <template v-else-if="tips === 'agentSetupKey'">
      <i18n tag="pre" :path="tips" v-if="!row.auth_type">
        <span class="danger">password</span>
        <span class="danger">mykeypair.pem</span>
      </i18n>
      <i18n tag="pre" :path="'agentSetupPwd'" v-else-if="row.auth_type === 'PASSWORD'">
        <span class="danger">password</span>
      </i18n>
      <i18n tag="pre" :path="'agentSetupFile'" v-else>
        <span class="danger">mykeypair.pem</span>
      </i18n>
    </template>
    <i18n tag="pre" :path="tips" v-else-if="tips === 'agentSetupLoginAccount'">
      <span class="danger">root</span>
    </i18n>
    <!-- eslint-disable-next-line vue/no-v-html -->
    <p v-else-if="['登录IP提示', '出口IP提示'].includes(tips)" v-html="$t(tips)"></p>
    <i18n tag="pre" :path="tips" v-else></i18n>
  </section>
</template>
<script lang="ts">
import { Vue, Component, Prop, Emit } from 'vue-property-decorator';
import { getDefaultConfig } from '@/config/config';
import { ISetupRow } from '@/types';
import { MainStore } from '@/store';

@Component({
  name: 'table-header-tip',
})
export default class TableHeader extends Vue {
  @Prop({ type: Boolean, default: false }) private readonly jointTip!: boolean;
  @Prop({ type: String, default: '' }) private readonly tips!: string; // 是否有悬浮提示
  @Prop({ type: Object, default: () => ({}) }) private readonly row!: ISetupRow;

  private get osNameList() {
    return MainStore.osNameList;
  }

  private get port() {
    if (this.row.os_type) {
      return `${getDefaultConfig(this.row.os_type, 'port')}  `;
    }
    let portText = '\n';
    this.osNameList.map((item) => {
      const name = item.toUpperCase();
      return  {
        name: item,
        port: getDefaultConfig(name, 'port'),
      };
    }).forEach((item) => {
      portText += `${item.name}: ${item.port}\n`;
    });
    return portText;
  }
  private get portDescription() {
    return this.row.os_type ? getDefaultConfig(this.row.os_type, 'port__description') : '';
  }

  @Emit('batch')
  public handleBatch() {}
}
</script>

<style lang="postcss">
.tips-content {
  .pointer {
    cursor: pointer;
  }
  .primary {
    color: #3a84ff
  }
  .danger {
    color: #ea3636;
  }
}
</style>
