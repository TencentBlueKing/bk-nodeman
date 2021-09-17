<template>
  <bk-sideslider
    transfer
    :is-show.sync="show"
    :width="540"
    :title="title"
    @hidden="handleToggle(false)">
    <template #content>
      <section class="channel-edit">
        <bk-form
          v-test="'channelForm'" form-type="vertical" :label-width="400" :model="channelForm" ref="channelFormRef">
          <bk-form-item :label="$t('通道名称')" property="name" required :rules="[required]">
            <bk-input v-model.trim="channelForm.name"></bk-input>
          </bk-form-item>
          <bk-form-item :label="$t('节点IP')" property="jump_servers" required :rules="ipRules">
            <bk-input v-model.trim="channelForm.jump_servers"></bk-input>
          </bk-form-item>
          <p class="mt30 mb10 upstream-node">{{ $t('上游节点信息') }}</p>
          <template v-for="(server, keyIndex) in channelServerKeys">
            <bk-form-item
              v-for="(item, index) in channelForm[server]"
              :class="{ 'item-label-none': index > 0, mt10: index > 0 }"
              :required="true"
              :icon-offset="58"
              :label="labelMap[server]"
              :rules="getIpRules(server)"
              :property="`${server}.${index}.value`"
              :key="`${keyIndex}_${index}`">
              <bk-input v-test="`formItem.${server}`" v-model.trim="item.value" :placeholder="$t('请输入')">
                <div class="input-control-slot" slot="append">
                  <i
                    :class="['nodeman-icon nc-plus', { 'disable-icon': btnLoading }]"
                    @click="handleControlServerNum(server, index, 'add')">
                  </i>
                  <i
                    :class="['nodeman-icon nc-minus', { 'disable-icon': channelForm[server].length <= 1 }]"
                    @click="handleControlServerNum(server, index, 'delete')">
                  </i>
                </div>
              </bk-input>
            </bk-form-item>
          </template>
          <bk-form-item class="mt30">
            <bk-button
              v-test.common="'formCommit'" theme="primary" :loading="btnLoading" @click.stop.prevent="handleSave">
              {{ confirmText }}
            </bk-button>
            <bk-button class="ml10" :disabled="btnLoading" @click="handleToggle(false)">
              {{ $t('取消') }}
            </bk-button>
          </bk-form-item>
        </bk-form>
      </section>
    </template>
  </bk-sideslider>
</template>
<script lang="ts">
import { Component, Prop, Vue, ModelSync, Emit, Watch, Ref } from 'vue-property-decorator';
import { CloudStore } from '@/store';

@Component
export default class ChannelEdit extends Vue {
  @ModelSync('value', 'change', { default: false, type: Boolean }) private show!: boolean;
  @Prop({ default: () => ({}), type: Object }) private readonly channel!: Dictionary;
  @Prop({ type: Boolean, default: false }) private readonly edit!: boolean;
  @Prop({ type: Number, default: -1 }) private readonly cloudId!: number;

  @Ref('channelFormRef') private readonly channelFormRef!: any;

  private required = {
    required: true,
    message: this.$t('必填项'),
    trigger: 'blur',
  };
  private ipRule = {
    regex: /^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$/,
    message: '请输入正确IP',
    trigger: 'blur',
  };
  private ipRules = [this.required, this.ipRule];
  private btnLoading = false;
  private channelForm: Dictionary = {};
  private labelMap: Dictionary = {
    btfileserver: 'Btfileserver',
    dataserver: 'Dataserver',
    taskserver: 'Taskserver',
  };

  private get title() {
    return this.edit ? this.$t('编辑安装通道') : this.$t('新建安装通道');
  }
  private get confirmText() {
    return this.edit ? this.$t('保存') : this.$t('提交');
  }
  private get channelServerKeys() {
    return CloudStore.channelServerKeys;
  }

  @Watch('show')
  public handleShowChange(show: boolean) {
    this.btnLoading = false;
    this.$set(this, 'channelForm', this.getFormatForm(show && this.edit ? this.channel : undefined));
  }

  @Emit('change')
  public handleToggle(show: boolean) {
    return show;
  }
  @Emit('channel-confirm')
  public handleChannelConfirm(channel: Dictionary) {
    this.handleToggle(false);
    return { channel };
  }

  public handleSave() {
    this.channelFormRef.validate().then(async () => {
      const { id, name, jump_servers: jumpServers } = this.channelForm;
      const params: Dictionary = {
        name,
        bk_cloud_id: this.cloudId,
        jump_servers: [jumpServers],
        upstream_servers: {},
      };
      this.channelServerKeys.forEach((key) => {
        params.upstream_servers[key] = this.channelForm[key].map((item: { value: string }) => item.value);
      });
      this.btnLoading = true;
      let res;
      if (this.edit) {
        res = await CloudStore.updateChannel({ id, params });
      } else {
        res = await CloudStore.createChannel(params);
      }
      this.btnLoading = false;
      if (this.edit ? res : res.id) {
        this.$bkMessage({
          theme: 'success',
          message: this.edit ? this.$t('修改成功') : this.$t('新增通道成功，请按照下方的部署指引进行节点部署'),
        });
        this.handleChannelConfirm(this.edit ? Object.assign({ id }, params) : res);
      }
    });
  }
  public handleControlServerNum(key: string, index: number, type: 'add' | 'delete') {
    if (type === 'add') {
      this.channelForm[key].splice(index + 1, 0, { value: '' });
    } else if (type === 'delete' && this.channelForm[key].length > 1) {
      this.channelForm[key].splice(index, 1);
    }
  }
  public getFormatForm(channel?: Dictionary) {
    const formData: Dictionary = {
      name: '',
      jump_servers: '',
    };
    if (channel) {
      Object.keys(channel).forEach((key) => {
        if (key === 'upstream_servers') {
          const { upstream_servers: upstream = {} } = channel;
          this.channelServerKeys.forEach((server) => {
            formData[server] = upstream[server]
              ? upstream[server].map((ip: string) => ({ value: ip }))
              : [{ value: '' }];
          });
        } else if (key === 'jump_servers') {
          const [jumpServers] = channel[key];
          formData[key] = jumpServers;
        } else {
          formData[key] = channel[key];
        }
      });
    } else {
      this.channelServerKeys.forEach((key) => {
        formData[key] = [{ value: '' }];
      });
    }
    return formData;
  }
  public getIpRules(key: string) {
    return [this.required, this.ipRule, {
      message: this.$t('冲突校验', { prop: 'IP' }),
      trigger: 'blur',
      validator: (value: string) => this.checkRepeatIp(value, key),
    }];
  }
  public checkRepeatIp(value: string, prop: string) {
    return this.channelForm[prop].filter((item: { value: string }) => item.value === value).length < 2;
  }
}
</script>
<style lang="postcss" scoped>
  .channel-edit {
    padding: 20px 30px;
  }
  .bk-form-item {
    >>> &.item-label-none .bk-label {
      display: none;
    }
    >>> .group-append {
      border: 0;
    }
  }
  .upstream-node {
    font-size: 14px;
    font-weight: 700;
  }
  .input-control-slot {
    display: flex;
    align-items: center;
    width: 50px;
    height: 100%;
    .nodeman-icon {
      margin-left: 9px;
      font-size: 16px;
      color: #c4c6cc;
      cursor: pointer;
      &:hover {
        color: #979ba5;
      }
      &.disable-icon {
        color: #dcdee5;
        cursor: not-allowed;
      }
    }
  }
</style>
