<template>
  <bk-sideslider
    ext-cls="commands-slider"
    transfer
    quick-close
    :width="620"
    :is-show="show"
    :title="$t('手动操作sliderTitle', [slider.opType, slider.row.innerIp])"
    :before-close="handleHidden">
    <div slot="content" class="commands-wrapper" v-bkloading="{ isLoading: commandLoading }">
      <!--
        Agent/PAgent/Proxy * Windows/Linux 6种情况
        直连linux：在机器上执行命令
        云区域linux、windows、proxy：在proxy上执行命令
        直连windows: 三个步骤
      -->
      <!-- 仅window agent（直连云区域0）有前两部 -->
      <p class="guide-title">
        {{ $t('手动操作指引', [slider.hostType === 'Agent' ? $t('主机') : 'Proxy', slider.opType, slider.hostType]) }}
      </p>
      <template v-if="slider.hostType === 'Agent' && hostSys === 'WINDOWS'">
        <p class="guide-title">
          1. {{ $t('windowsStrategy1Before') }}
          <a class="guide-link" :href="curlUrl" target="_blank"> curl.exe </a>
          {{ $t('windowsStrategy1After') }}
        </p>
        <p class="guide-title">2. {{ $t('windowsStrategy2') }}</p>
      </template>

      <!-- 共有的 -->
      <p class="guide-title">
        <template v-if="hostSys === 'WINDOWS'">3.</template>
        {{ $t('执行以下操作命令') }}
        <bk-popover
          ref="popover"
          trigger="click"
          theme="light silder-guide"
          placement="bottom-start">
          <span class="guide-link pointer">{{ $t('网络策略开通指引') }}</span>
          <template #content>
            <StrategyTemplate
              v-if="slider.show"
              class="operation-tips"
              :host-type="slider.hostType"
              :host-list="hostList">
            </StrategyTemplate>
          </template>
        </bk-popover>
      </p>
      <Tips class="mb20" v-if="hostSys !== 'WINDOWS'">
        <template #default>
          <i18n tag="p" path="请将操作指令中的数据替换再执行">
            <span class="tips-text-decs">{{ $t('账号') }}</span>
            <span class="tips-text-decs">{{ $t('端口') }}</span>
            <span class="tips-text-decs">{{ $t('密码密钥') }}</span>
            <span class="tips-text-decs">{{ $t('真实数据') }}</span>
          </i18n>
        </template>
      </Tips>
      <template v-if="!commandError">
        <ul class="commands-list" v-if="commandData.length">
          <li class="commands-item"
              v-for="(item, index) in commandData"
              :key="item.cloudId">
            <p class="commands-title mb10" v-if="!slider.isSingle">{{ item.cloudName }}</p>
            <div :class="['command-conatainer', { 'fold': item.isFold, 'single': slider.isSingle }]">
              <!-- eslint-disable-next-line vue/no-v-html -->
              <div v-html="slider.isSingle ? item.command : item.totalCommands"
                   class="commands-left" :ref="`commanad${ item.cloudId }`">
              </div>
              <div class="commands-right">
                <p>
                  <i class="nodeman-icon nc-copy command-icon" v-bk-tooltips="{
                    delay: [300, 0],
                    content: $t('复制命令')
                  }" @click="copyCommand(item, index)"></i>
                </p>
              </div>
            </div>
          </li>
        </ul>
        <ExceptionCard v-else type="dataAbnormal"></ExceptionCard>
      </template>
    </div>
  </bk-sideslider>
</template>

<script lang="ts">
import { Vue, Component, Prop, Model, Emit, Watch } from 'vue-property-decorator';
import Tips from '@/components/common/tips.vue';
import StrategyTemplate from '@/components/common/strategy-template.vue';
import ExceptionCard from '@/components/exception/exception-card.vue';
import { copyText } from '@/common/util';
import { AgentStore, TaskStore } from '@/store';
import { ITaskHost } from '@/types/task/task';

@Component({
  name: 'TaskDetailSlider',
  components: {
    Tips,
    StrategyTemplate,
    ExceptionCard,
  },
})
export default class TaskDetailSlider extends Vue {
  @Model('update', { default: false }) private readonly show!: boolean;
  @Prop({ type: Object, default: () => ({ row: {} }) }) private readonly slider!: Dictionary;
  @Prop({ type: String, default: '' }) private readonly title!: string;
  @Prop({ type: [String, Number], default: '' }) private readonly taskId!: string | number;
  @Prop({ type: String, default: '' }) private readonly operateHost!: string;
  @Prop({ type: Array, default: () => [] }) private readonly tableList!: ITaskHost[];

  private commandLoading = false;
  private commandData: any[] = [];
  private commandError = false;
  private hostSys = '';

  private get hostList() {
    const list = this.tableList.map(item => ({
      bk_cloud_id: item.bkCloudId,
      bk_cloud_name: item.bkCloudName,
      ap_id: item.apId,
      inner_ip: item.innerIp,
    }));
    list.sort((a, b) => a.bk_cloud_id - b.bk_cloud_id);
    return list;
  }

  private get curlUrl() {
    const ap = AgentStore.apList.find(item => item.id === this.slider.row.apId);
    if (ap) {
      const { bkCloudId } = this.slider.row;
      const packageUrl = bkCloudId === 0 ? ap.package_inner_url : ap.package_outer_url;
      return packageUrl.endsWith('/') ? `${packageUrl}curl.exe ` : `${packageUrl}/curl.exe `;
    }
    return '';
  }

  @Watch('show')
  public handleShowChange(isShow: boolean) {
    if (isShow) {
      this.commandError = false;
      this.requestCommandData(this.slider.row);
    } else {
      this.commandLoading = false;
    }
  }

  // 每次点击都需要获取最新的命令
  public async requestCommandData(row: any) {
    if (!this.commandLoading) {
      this.commandLoading = true;
      const res = await TaskStore.requestCommands({
        jobId: this.taskId as number,
        params: { bk_host_id: row ? row.bkHostId : -1 },
      });
      if (res) {
        const data = [];
        if (row) {
          const cloudCommand = res[row.bkCloudId];
          const curCommand = cloudCommand
            ? cloudCommand.ipsCommands.find((item: any) => item.ip === row.innerIp) : null;
          this.hostSys = curCommand ? curCommand.osType : '';
          if (curCommand) {
            data.push(Object.assign({
              isFold: false,
              cloudId: row.cloudId,
            }, curCommand));
          }
        // 批量查看命令 - 目前用不到了
        } else {
          Object.keys(res).forEach((key) => {
            const commandItem = {
              isFold: false,
              cloudId: parseInt(key, 10),
              cloudName: '',
            };
            if (parseInt(key, 10) === window.PROJECT_CONFIG.DEFAULT_CLOUD) {
              commandItem.cloudName = window.i18n.t('直连区域');
            } else {
              const cloud = AgentStore.cloudList.find(item => `${item.bk_cloud_id}` === key
                              || item.bk_cloud_id === window.PROJECT_CONFIG.DEFAULT_CLOUD);
              commandItem.cloudName = cloud ? cloud.bk_cloud_name : key;
            }
            data.push(Object.assign(commandItem, res[key]));
          });
        }
        this.commandData = data;
      }
      this.commandError = !res;
      this.commandLoading = false;
      return !res;
    }
    return false;
  }
  public async copyCommand(row: any, index: number) {
    if (!row || this.commandLoading) {
      return false;
    }
    const hasCommand = Object.prototype.hasOwnProperty.call(row, 'isFold'); // dialog里的复制不需要重新加载数据
    let res = true;
    if (!hasCommand) {
      res = await this.requestCommandData(row);
    }
    let commandStr = '';
    if (hasCommand) {
      const ref = this.$refs[`commanad${row.cloudId}`] as any[];
      commandStr = ref ? ref[index].textContent : '';
    } else {
      const cloud = this.commandData.find(item => item.cloudId === row.bkCloudId);
      const commandList = cloud ? cloud.ipsCommands : [];
      const commandItem = commandList.find((item: any) => item.ip === row.innerIp);
      commandStr = commandItem ? commandItem.command.replace(/<[^>]+>/gi, '') : '';
    }
    if (res && commandStr) {
      copyText(commandStr, () => {
        this.$bkMessage({
          theme: 'success',
          message: this.$t('命令复制成功'),
        });
      });
    }
  }

  @Emit('update')
  public handleHidden() {
    return false;
  }
}
</script>

<style lang="postcss" scoped>
  .task-detail-wrapper {
    .tips-text-decs {
      color: #313238;
    }
    .execut-text {
      &.has-icon {
        cursor: pointer;
      }
      &:hover .filtered-icon {
        color: #3a84ff;
      }
    }
  }
  /deep/ .row-select .cell {
    padding-left: 24px;
    padding-right: 0;
  }
  /deep/ .row-ip .cell {
    padding-left: 24px;
  }
  /deep/ .row-select .cell {
    padding-left: 24px;
    padding-right: 0;
  }
  .guide-title {
    margin: 0 0 14px 0;
    .guide-link {
      color: #3a84ff;
      &.pointer {
        cursor: pointer;
      }
    }
  }
  .commands-slider {
    .commands-wrapper {
      padding: 24px 30px;
      min-height: calc(100vh - 52px);
      overflow: auto;
    }
    .commands-item {
      margin-bottom: 20px;
      &:last-child {
        margin-bottom: 0;
      }
    }
    .commands-title {
      font-size: 14px;
      color: #63656e;
    }
    .command-conatainer {
      position: relative;
      padding: 12px 28px 16px 20px;
      border: 1px solid #dcdee5;
      border-radius: 2px;
      background: #fafbfd;
      .commands-left {
        width: 100%;
        max-height: 128px;
        min-height: 22px;
        line-height: 18px;
        font-size: 12px;
        color: #979ba5;
        overflow-x: hidden;
        overflow-y: auto;
        word-break: break-all;
        >>> span {
          color: #313238;
        }
      }
      &.fold {
        padding: 7px 10px;
        .commands-left {
          padding-right: 56px;
          white-space: nowrap;
          text-overflow: ellipsis;
          overflow: hidden;
        }
      }
      &.single .commands-left {
        max-height: none;
      }
      .commands-right {
        position: absolute;
        right: 5px;
        bottom: 5px;
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
        width: 46px;
        line-height: 18px;
        font-size: 17px;
        text-align: right;
      }
      .command-icon {
        color: #979ba5;
        cursor: pointer;
        &:hover {
          color: #63656e;
        }
      }
    }
  }
  .operation-tips {
    max-height: 600px;
    overflow: auto;
  }
</style>
