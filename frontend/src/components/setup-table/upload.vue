<template>
  <div class="upload">
    <div v-if="!Object.keys(file).length" class="upload-wrapper">
      <bk-button ext-cls="upload-btn">
        <span class="upload-btn-content">
          <i :class="icon" :style="{ 'font-size': iconSize + 'px' }"></i>
          <span>{{ title }}</span>
        </span>
      </bk-button>
      <input
        ref="uploadel"
        @change="handleChange"
        :accept="accept"
        :multiple="false"
        :name="name"
        title=""
        type="file"
        class="upload-input">
    </div>
    <slot name="uploadInfo" v-bind="{ file, fileChange: handleChange }" v-else>
      <div class="upload-info"
           :class="{ hover: hoverInfo && !disableHoverCls }"
           @mouseenter="handleMouseEnter"
           @mouseleave="handleMouseLeave">
        <div class="info-left">
          <i :class="fileIcon"></i>
        </div>
        <div class="info-right ml5">
          <div class="info-name">
            <span class="file-name" :title="file.name">{{ file.name || 'name' }}</span>
            <span class="file-extension">{{ file.extension || '' }}</span>
            <i class="file-abort nodeman-icon nc-delete" @click="handleAbortUpload" v-show="hoverInfo"></i>
          </div>
          <div class="info-progress" v-show="file.percentage !== '100%'">
            <div class="progress-bar"
                 :class="{ 'fail-background': file.hasError }"
                 :style="{ width: file.percentage || 0 }">
            </div>
          </div>
        </div>
      </div>
    </slot>
  </div>
</template>

<script lang="ts">
import { Vue, Component, Model, Prop, Emit, Ref, Watch } from 'vue-property-decorator';
import { IFileInfo } from '@/types';
import { OutgoingHttpHeaders } from 'http';
import i18n from '@/setup';

interface IObject {
  [key: string]: any
}

@Component({ name: 'upload' })

export default class Upload extends Vue {
  @Model('change') private readonly value!: string;

  @Prop({ type: String, default: 'file_data' }) private readonly name!: string; // 上传至服务器的名称
  @Prop({ type: String, default: '' }) private readonly accept!: string; // mime类型
  @Prop({ type: String, default: i18n.t('版本包文件类型') }) public readonly acceptDesc!: string; // mime类型提示
  @Prop({ type: String, default: i18n.t('文件类型不符') }) private readonly acceptTips!: string; // 类型错误提示信息
  @Prop({ type: String, default: '' }) private readonly action!: string; // URL
  @Prop({ type: Number, default: 500 }) private readonly maxSize!: number; // 最大文件大小,单位M
  @Prop({ type: String, default: 'MB', validator(v: string) {
    return ['KB', 'MB'].includes(v);
  } }) private readonly unit!: string;
  @Prop({ type: [Array, Object], default: () => ([]) }) private readonly headers!: OutgoingHttpHeaders; // 请求头
  @Prop({ type: Boolean, default: false }) private readonly withCredentials!: boolean;
  @Prop({ type: Function, default: () => {} }) private readonly onUploadError!: Function; // 上传失败回调
  @Prop({ type: Function, default: () => {} }) private readonly onUploadSuccess!: Function; // 上传成功回调
  @Prop({ type: Function, default: () => {} }) private readonly onUploadProgress!: Function; // 上传进度回调
  @Prop({ type: String, default: 'bk-icon icon-plus' }) private readonly icon!: string; // 上传text图标
  @Prop({ type: String, default: 'nodeman-icon nc-key' }) private readonly fileIcon!: string;
  @Prop({ type: [Number, String], default: '22' }) private readonly iconSize!: string | number;
  @Prop({ type: String, default: window.i18n.t('上传文件') }) private readonly title!: string; // 上传按钮文字信息
  @Prop({ type: Boolean, default: false }) private readonly parseText!: boolean; // 是否前端解析
  @Prop({ type: Boolean, default: false }) private readonly disableHoverCls!: boolean; // 禁用文件框悬浮样式
  @Prop({ type: Object, default: () => ({}) }) private readonly fileInfo!: IFileInfo; // 回显文件信息
  @Prop({ type: Object, default: () => ({}) }) private readonly attached!: Dictionary; // 附带的参数

  @Ref('uploadel') private readonly uploadel: any;

  // eslint-disable-next-line @typescript-eslint/consistent-type-assertions
  private file: IFileInfo = {} as IFileInfo; // 当前文件对象
  private reqsMap: IObject = {}; // 文件请求Map（用于终止）
  private fileIndex = 1; // 文件索引
  private hoverInfo = false; // 鼠标悬浮状态

  private get maxFileSize(): number {
    switch (this.unit) {
      case 'KB':
        return this.maxSize * (2 ** 10);
      case 'MB':
        return this.maxSize * (2 ** 20);
      default:
        return this.maxSize * (2 ** 20);
    }
  }
  @Watch('fileInfo', { immediate: true })
  public handleFileChange(v: IFileInfo) {
    if (v && Object.keys(v).length) {
      this.file = JSON.parse(JSON.stringify(this.fileInfo));
    }
  }

  @Emit('change')
  public handleEmitChange(value: string, fileInfo: IFileInfo) {
    return { value, fileInfo };
  }

  // 文件变更
  public handleChange(e: Event) {
    const { files } = e.target as any;
    const [file] = Array.from(files) as  File[];
    if (this.validateFile(file)) {
      // eslint-disable-next-line @typescript-eslint/consistent-type-assertions
      this.file = {} as IFileInfo;
      this.parseText ? this.handleParseText(file) : this.handleUploadFiles(file);
      this.uploadel.value = '';
    }
    this.uploadel.value = '';
  }
  // 组装文件对象，添加额外属性
  public handleAssembleFile(file: File): IFileInfo {
    const ext = file.name.slice((file.name.lastIndexOf('.') - 1 >>> 0) + 1);
    const fileName = file.name.substring(0, file.name.lastIndexOf(ext));
    const uid = this.fileIndex;
    this.fileIndex += 1;
    return {
      name: fileName,
      type: file.type,
      size: file.size,
      percentage: '',
      uid: Date.now() + uid,
      originFile: file,
      status: 'uploading',
      hasError: false,
      errorMsg: '',
      extension: ext,
    };
  }
  // 校验文件
  public validateFile(file: File) {
    if (!file) return false;
    const validate = {
      message: '',
      success: true,
    };
    if (file.size > this.maxFileSize) {
      validate.success = false;
      validate.message = `文件不能超过 ${this.maxSize} ${this.unit}`;
    }
    if (this.accept && !this.accept.split(',').includes(file.type)) {
      validate.success = false;
      validate.message = this.acceptTips;
    }
    if (!validate.success) {
      this.$bkMessage({
        theme: 'error',
        message: validate.message,
      });
    }
    return validate.success;
  }
  // 前端解析上传文件
  public handleParseText(file: File) {
    // 修改原file对象的属性
    this.file = this.handleAssembleFile(file);
    const fileReader = new FileReader();
    fileReader.onload = (ev: Event) => {
      try {
        const key: string = (ev.target as any).result;
        this.handleEmitChange(key, this.file);
        this.onUploadSuccess(key, this.file);
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e || this.$t('解析文件失败'),
        });
        this.file.hasError = true;
        this.onUploadError(e, this.file);
      }
    };
    fileReader.onprogress = (ev: Event) => {
      const { loaded, total } = ev as any;
      const percentage = `${(loaded / total) * 100}`;
      this.file.percentage = `${parseInt(percentage, 10)}%`;
    };
    fileReader.readAsText(file);
  }
  // 上传文件
  @Emit('before-upload')
  public handleUploadFiles(file: File) {
    // 修改原file对象的属性
    this.file = this.handleAssembleFile(file);
    const { originFile, uid } = this.file;
    const options = {
      headers: this.headers,
      withCredentials: this.withCredentials,
      file: originFile,
      filename: this.name,
      action: this.action,
      onProgress: (e: Event) => {
        this.handleHttpProgress(e, originFile);
      },
      onSuccess: (res: any) => {
        this.handleHttpSuccess(res, originFile);
        delete this.reqsMap[uid];
      },
      onError: (err: any) => {
        this.handleHttpError(err, originFile);
        delete this.reqsMap[uid];
      },
    };
    const req = this.handleHttpRequest(options);
    this.reqsMap[uid] = req;
    return false;
  }
  // 终止文件上传
  public handleAbortUpload() {
    if (this.file.uid && this.reqsMap[this.file.uid]) {
      this.reqsMap[this.file.uid].abort();
      delete this.reqsMap[this.file.uid];
    }
    // eslint-disable-next-line @typescript-eslint/consistent-type-assertions
    this.file = {} as IFileInfo;
    this.hoverInfo = false;
    this.handleEmitChange('', this.file);
  }
  // 发送HTTP请求
  public handleHttpRequest(option: IObject) {
    if (typeof XMLHttpRequest === 'undefined') return;

    const xhr = new XMLHttpRequest();
    if (xhr.upload) {
      xhr.upload.onprogress = (e: any) => {
        if (e.total > 0) {
          e.percent = Math.round((e.loaded * 100) / e.total);
        }
        option.onProgress(e);
      };
    }

    const formData = new FormData();
    formData.append(option.filename, option.file, option.file.name);
    try {
      if (typeof this.attached === 'object') {
        Object.keys(this.attached).forEach((key) => {
          formData.append(key, this.attached[key]);
        });
      }
    } catch (_) {}
    xhr.onerror = (e) => {
      option.onError(e);
    };

    const { action } = option;
    xhr.onload = () => {
      const { result, code } = JSON.parse(xhr.response);
      // 3800002 包管理 - 包名重复
      if (xhr.status < 200 || xhr.status >= 300 || (!result && code !== 3800002)) {
        return option.onError(this.onError(action, xhr));
      }
      option.onSuccess(this.onSuccess(xhr));
    };
    xhr.open('post', action, true);

    if ('withCredentials' in xhr) {
      xhr.withCredentials = option.withCredentials;
    }
    const { headers } = option;
    if (headers) {
      if (Array.isArray(headers)) {
        headers.forEach((head) => {
          const headerKey = head.name;
          const headerVal = head.value;
          xhr.setRequestHeader(headerKey, headerVal);
        });
      } else {
        const headerKey = headers.name;
        const headerVal = headers.value;
        xhr.setRequestHeader(headerKey, headerVal);
      }
    }
    xhr.send(formData);
    return xhr;
  }
  // 默认失败回调
  public onError(action: string, xhr: XMLHttpRequest) {
    let msg;
    if (xhr.response) {
      try {
        msg = `${JSON.parse(xhr.response).message || xhr.response}`;
      } catch (_) {
        msg = xhr.response;
      }
    } else if (xhr.responseText) {
      msg = `${xhr.responseText}`;
    } else {
      msg = `fail to post ${action} ${xhr.status}`;
    }

    const err: any = new Error(msg);
    err.status = xhr.status;
    err.method = 'post';
    err.url = action;
    return err;
  }
  // 默认成功回调
  public onSuccess(xhr: XMLHttpRequest) {
    const text = xhr.responseText || xhr.response;
    if (!text) return text;

    try {
      return JSON.parse(text);
    } catch (e) {
      return text;
    }
  }
  // 获取进度并触发props函数
  public handleHttpProgress(e: any, postFiles: File) {
    this.file.percentage = `${e.percent}%`;
    this.file.status = 'uploading';
    this.onUploadProgress(e, postFiles);
  }
  // 成功处理并触发props函数
  public handleHttpSuccess(res: any, postFiles: File) {
    this.file.status = 'success';
    this.onUploadSuccess(res, postFiles);
  }
  // 失败处理并触发props函数
  public handleHttpError(err: any, postFiles: File) {
    this.file.hasError = true;
    this.file.errorMsg = err.message;
    this.file.status = 'error';
    this.onUploadError(err, postFiles);
  }
  // 鼠标悬浮
  public handleMouseEnter() {
    this.hoverInfo = true;
  }
  // 鼠标离开
  public handleMouseLeave() {
    this.hoverInfo = false;
  }
  // 文件上传重试
  public handleRetry() {
    if (this.file.originFile) {
      this.handleUploadFiles(this.file.originFile);
    }
  }
}
</script>
<style lang="postcss" scoped>
  @import "@/css/mixins/nodeman.css";

  .upload-wrapper {
    position: relative;
    &:hover {
      button {
        border-color: #979ba5;
        color: #63656e;
      }
    }
    .upload-btn {
      width: 100%;
    }
    .upload-btn-content {
      position: relative;
      left: -2px;

      @mixin layout-flex row, center, center;
      i {
        top: 0;
      }
    }
    .upload-input {
      position: absolute;
      left: 0;
      top: 0;
      width: 100%;
      height: 100%;
      cursor: pointer;
      opacity: 0;
    }
  }
  .upload-info {
    padding-left: 2px;
    padding-right: 5px;
    height: 32px;

    @mixin layout-flex row, center;
    &.hover {
      background: #f0f1f5;
      border-radius: 2px;
    }
    .info-left {
      font-size: 18px;
      color: #c4c6cc;
    }
    .info-right {
      width: 0;
      flex: 1;
      .info-name {
        position: relative;
        line-height: 16px;

        @mixin layout-flex row;
        .file-name {
          height: 16px;
          word-break: break-all;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .file-extension {
          margin-right: 20px;
        }
        .file-abort {
          position: absolute;
          right: 0;
          font-size: 18px;
          cursor: pointer;
        }
      }
      .info-progress {
        width: 100%;
        height: 2px;
        background: #dcdee5;
        border-radius: 1px;
        .progress-bar {
          height: 2px;
          border-radius: 1px;
          background: #3a84ff;
          transition: width .3s ease-in-out;
        }
      }
    }
  }
</style>
