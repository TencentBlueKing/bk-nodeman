<template>
  <bk-sideslider
    transfer
    quick-close
    :is-show="show"
    :width="960"
    :title="$t('包上传')"
    :before-close="handleToggle">
    <template #content>
      <section class="package-upload">
        <div class="upload-component">
          <!--
            tar: application/x-tar
            tgz: application/x-compressed
            gz: application/x-gzip; application/gzip
          -->
          <Upload
            ref="pkgUploadRef"
            name="package_file"
            accept="application/x-compressed,application/x-gzip,application/gzip"
            :accept-desc="$t('支持 tgz、tar、gz 扩展名格式文件')"
            :action="`${baseUrl}api/agent/package/upload/`"
            :headers="uploadHeader"
            :attached="pckWarning === 'before' ? { overload: true } : {}"
            :on-upload-success="handleUploadSuccess"
            :on-upload-error="handleUploadError"
            :on-upload-progress="handleUploadProgress">
            <template v-if="pckWarning" #success>
              <bk-popover
                v-if="pckWarning === 'before'"
                ext-cls="upload-conflict-popover"
                theme="light"
                placement="bottom-start"
                :always="true">
                <div class="upload-conflict">
                  <i class="bk-icon icon-exclamation-circle" />
                  <span>{{ $t('存在同名 Agent 包') }}</span>
                </div>
                <div slot="content">
                  <p class="upload-conflict-title">{{ $t('存在同名Agent包，是否覆盖上传？') }}</p>
                  <p class="upload-conflict-line">{{ $t('包覆盖包名：', [pkgFileName]) }}</p>
                  <p class="upload-conflict-line">{{ $t('包覆盖MD5：', [pkgFileMd5]) }}</p>
                  <p class="upload-conflict-line">{{ $t('继续上传，将会覆盖当前平台同名的 Agent 包') }}</p>
                  <div class="upload-conflict-footer">
                    <bk-button theme="primary" :loading="pkgLoading" size="small" @click="uploadCover">
                      {{ $t('覆盖上传') }}
                    </bk-button>
                    <bk-button size="small" @click="handleToggle">{{ $t('取消上传') }}</bk-button>
                  </div>
                </div>
              </bk-popover>
              <div v-else class="upload-conflict success">
                <!-- <div v-else class="upload-conflict success"> -->
                <i class="bk-icon icon-check-1" />
                <span>{{ $t('上传成功（存在同名 Agent 包，确认覆盖上传）') }}</span>
              </div>
            </template>
          </Upload>
        </div>
        <template v-if="pckUploaded">
          <div class="upload-result">
            <p class="upload-item-title">{{ $t('结果预览') }}</p>
            <bk-table class="pkg-manage-table pkg-parse-table" col-border :data="tableData">
              <NmColumn :label="$t('包名')" prop="pkg_name" width="260" />
              <NmColumn :label="$t('操作系统架构')" prop="sys" width="160">
                <template #default="{ row }">
                  {{ `${row.os}_${row.cpu_arch}` }}
                </template>
              </NmColumn>
              <NmColumn :label="$t('包类型')" prop="project" width="120">
                <template #default="{ row }">
                  {{ pkgType[row.project] }}
                </template>
              </NmColumn>
              <NmColumn :label="$t('标签信息')" prop="tags" :show-overflow-tooltip="false" :render-header="editTheadRender">
                <FlexibleTag :list="tagsDisplay" />
              </NmColumn>
            </bk-table>
          </div>
          <div class="upload-table">
            <p class="upload-item-title">{{ $t('描述') }}</p>
            <!-- 文本和标签不要换行 -->
            <pre class="upload-package-desc" v-bk-tooltips="$t('从包中解析的描述文本，不可修改')">{{ pkgDesc }}</pre>
          </div>
        </template>
      </section>
      <div class="upload-footer mt32">
        <bk-popover :disabled="pckUploaded" :content="$t('请先上传包文件')">
          <bk-button :disabled="!pckUploaded" :loading="submitLoading" theme="primary" @click="registerPkg">
            {{ $t('提交') }}
          </bk-button>
        </bk-popover>
        <bk-button @click="handleToggle">{{ $t('取消') }}</bk-button>
      </div>
    </template>
  </bk-sideslider>
</template>
<script lang="ts">
import i18n from '@/setup';
import { AgentStore } from '@/store';
import { defineComponent, getCurrentInstance, reactive, ref, Ref, toRefs, watch, inject, CreateElement, PropType } from 'vue';
import cookie from 'cookie';
import Upload from '@/components/common/upload.vue';
import FlexibleTag from '@/components/common/flexible-tag.vue';
import PkgThead from './PkgThead.vue';
import { IpkgParseInfo, PkgType } from '@/types/agent/pkg-manage';
import { uuid } from '@/components/RussianDolls/create';
import { IBkColumn, ISearchItem } from '@/types';

interface IUploadInfo {
  id: number;
  name: string;
  pkg_size: string;
}

export default defineComponent({
  components: {
    Upload,
    FlexibleTag,
  },
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    active: {
      type: String as PropType<PkgType>,
      default: 'gse_agent',
    },
  },
  emits: ['toggle', 'submit'],
  setup(props, { emit }) {
    const { proxy } = (getCurrentInstance() || {});
    const pkgUploadRef = ref<any>();

    const tagGroup = inject<Ref<ISearchItem[]>>('tagGroup');
    const tagsMap = inject<Ref<{ [k: string]: string }>>('tagsMap');

    const state = reactive({
      baseUrl: `${window.PROJECT_CONFIG.SITE_URL}${AJAX_URL_PREFIX}`,
      uploadHeader: [
        { name: 'X-REQUESTED-WITH', value: 'XMLHttpRequest' },
        { name: 'X-CSRFToken', value: cookie.parse(document.cookie)[`${window.PROJECT_CONFIG.APP_CODE}_csrftoken`] },
      ],
      pkgType: {
        gse_agent: 'Agent',
        gse_proxy: 'Proxy',
      },
      submitLoading: false,
      pkgLoading: false,
      pckUploaded: false,
      pkgFileName: '',
      pkgFileMd5: '',
      pkgDesc: '',
      pckWarning: '', // before, after
    });
    const taskState = reactive<{
      taskTimer: null | number;
      taskId: string;
    }>({
      taskTimer: null,
      taskId: '',
    });

    // 小包标的签一致; 内置标签不能删除; 仅能调整自定义标签;
    const tableData = ref<IpkgParseInfo[]>([]);
    const selectedTags = ref<string[]>([]);
    const tagsDisplay = ref<{ id: string; name: string; }[]>([]);

    const handleToggle = () => {
      emit('toggle');
    };

    const handleUploadSuccess = (res: { code: number; result?: boolean; data: IUploadInfo }) => {
      state.pkgLoading = false;
      if (res.code === 3800002) { // result === false
        state.pckWarning = 'before';
        return;
      }
      if (res.result) {
        state.pkgFileName = res.data.name;
        state.pkgFileMd5 = res.data.pkg_size;
        state.pckWarning =  state.pckWarning === 'before' ? 'after' : '';
        if (state.pckWarning !== 'before') {
          parsePkg();
        }
      }
    };
    const handleUploadError = () => {
      state.pkgLoading = false;
    };
    const handleUploadProgress = () => {
      state.pkgLoading = true;
    };

    // 包解析
    const parsePkg = async () => {
      const res = await AgentStore.apiPkgParse({ file_name: state.pkgFileName });
      if (res) {
        const {
          packages = [],
          description = '',
        } = res;
        state.pckUploaded = true;
        state.pkgDesc = description;
        tableData.value.splice(0, tableData.value.length, ...packages);
      }
    };
    const pollRegisterTask = () => {
      if (!taskState.taskId) {
        taskState.taskTimer && clearTimeout(taskState.taskTimer);
        return;
      }
      taskState.taskTimer = window.setTimeout(async () => {
        const { status } = await AgentStore.apiPkgRegisterQuery({ task_id: taskState.taskId });
        if (status === 'PENDING') {
          pollRegisterTask();
        } else {
          state.submitLoading = false;
          taskState.taskId = '';
          const isSucc = status === 'SUCCESS';
          proxy?.$bkMessage({
            theme: isSucc ? 'success' : 'error',
            message: isSucc ? i18n.t('注册成功') : i18n.t('注册失败'),
          });
          if (isSucc) {
            emit('toggle');
            emit('submit');
          }
        }
      }, 3000);
    };

    // 包注册任务
    const registerPkg = async () => {
      state.submitLoading = true;
      // 注册之前需要把新增的标签通过接口生成，然后拿到name给注册接口使用;
      const copyNameMap = { ...tagsMap?.value };
      const tags = selectedTags.value.filter(tag => !!copyNameMap[tag])
        .map(description => ({ name: `custom_${uuid(6)}`,  description }));
      let createTagsRes = !tags.length; // 创建标签的结果
      // 生成新标签
      if (tags.length) {
        const list = await AgentStore.apiPkgCreateTags({ project: props.active, tags });
        if (list) {
          createTagsRes = true;
          // 把创建好的标签合并至 copyNameMap
          Object.assign(copyNameMap, list.reduce((obj: { [k: string]: string }, item) => {
            Object.assign(obj, { [item.description]: item.name });
            return obj;
          }, {}));
        }
      }
      // 注册操作- 确认不需要生成 tags 或 生成tags成功之后进行
      if (createTagsRes) {
        const res = await AgentStore.apiPkgRegister({
          file_name: state.pkgFileName,
          tags: selectedTags.value.map(tag => copyNameMap[tag]), // tag的name
        });
        // 注册之后需要轮询这个任务
        if (res.task_id) {
          taskState.taskId = res.task_id;
          pollRegisterTask();
        } else {
          state.submitLoading = true;
        }
      }
    };

    // 覆盖之前的上传 - overload
    const uploadCover = () => pkgUploadRef.value?.handleRetry?.();


    const editTheadRender = (h: CreateElement, { column }: { column: IBkColumn }) => {
      const { label } = column;
      return h(PkgThead, {
        props: {
          label,
          type: '',
          batch: true,
          options: tagGroup?.value || [],
          moduleValue: selectedTags.value,
        },
        on: {
          confirm: ({ value }: { value: string[] }) => {
            selectedTags.value.splice(0, selectedTags.value.length, ...value);
            tagsDisplay.value.splice(0, tagsDisplay.value.length, ...value
              .map(id =>  ({
                id,
                name: tagsMap?.value[id] || id,
                className: tagsMap?.value[`${id}_class`],
              })));
          },
        },
      });
    };

    watch(() => props.show, (isShow) => {
      if (!isShow) {
        taskState.taskTimer && clearTimeout(taskState.taskTimer);
        state.submitLoading = true;
        state.pkgLoading = false;
        state.pckUploaded = false;
        state.pckWarning = '';
        taskState.taskId = '';
        selectedTags.value.splice(0, selectedTags.value.length);
        tagsDisplay.value.splice(0, selectedTags.value.length);
      }
    });

    // tesing;
    // state.pckWarning = '';
    // state.pckUploaded = true;
    // parsePkg();

    return {
      pkgUploadRef,
      tagsMap,
      ...toRefs(props),
      ...toRefs(state),
      ...toRefs(taskState),
      tableData,
      selectedTags,
      tagsDisplay,

      handleToggle,
      handleUploadSuccess,
      handleUploadError,
      handleUploadProgress,
      uploadCover,
      registerPkg,
      editTheadRender,
    };
  },
});
</script>
<style lang="postcss">
@import "@/css/variable.css";

.package-upload {
  height: calc(100vh - 108px);
  padding: 30px 40px;
  overflow-y: auto;

  .upload-result {
    margin-top: 24px;
  }

  .upload-conflict {
    display: flex;
    color: $bgWarning;
    .bk-icon {
      margin-right: 6px;
    }
    &.success {
      color: $bgSuccess;
    }
  }

  .upload-item-title {
    margin-top: 24px;
    margin-bottom: 8px;

  }

  .upload-package-desc {
    margin: 0;
    padding: 6px 10px;
    line-height: 20px;
    min-height: 40px;
    border: 1px solid #c4c6cc;
    border-radius: 2px;
    cursor: not-allowed;
    background-color: #fafbfd;
  }

  .pkg-parse-table {
    th {
      background-color: #f0f1f5;
    }
    td {
      background-color: #fafbfd;
      &:last-child {
        background-color: #fff;
      }
    }
  }

}

.upload-footer {
  display: flex;
  padding: 12px 40px;
  background-color: #fff;
  .bk-button {
    margin-right: 8px;
    min-width: 88px;
  }
}

.upload-conflict-popover {
  padding: 10px;
  .upload-conflict-title {
    margin-bottom: 8px;
    line-height: 24px;
    font-size: 16px;
    color: #313238;
  }
  .upload-conflict-line {
    line-height: 24px;
    font-size: 12px;
    color: #63656e;
  }
  .upload-conflict-footer {
    display: flex;
    justify-content: flex-end;
    margin-top: 12px;
    .bk-button {
      margin-left: 8px;
    }
  }
}
</style>
