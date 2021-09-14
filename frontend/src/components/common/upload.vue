<template>
  <div class="upload">
    <div class="upload-content">
      <div
        v-if="!Object.keys(file).length"
        class="upload-content-file"
        :class="{ 'hover': hoverInfo }"
        @mouseenter="handleMouseEnter"
        @mouseleave="handleMouseLeave">
        <i class="file-icon nodeman-icon nc-upload-cloud" :class="{ 'hover': hoverInfo }"></i>
        <i18n path="将文件拖到此处或" class="file-tips mt5">
          <span class="btn">{{ $t('点击上传') }}</span>
        </i18n>
        <input
          v-test.common="'fileInput'"
          ref="uploadel"
          @change="handleChange"
          :accept="accept"
          :multiple="false"
          :name="name"
          title=""
          type="file"
          class="file-input">
      </div>
      <div class="upload-content-info"
           :class="{ 'loading': file.status === 'uploading', 'error': file.status === 'error' }"
           @mouseenter="handleMouseEnter"
           @mouseleave="handleMouseLeave"
           v-else>
        <i class="abort-icon nodeman-icon nc-delete"
           v-show="file.status === 'uploading' && hoverInfo"
           @click="handleAbortUpload">
        </i>
        <!-- eslint-disable-next-line vue/max-len -->
        <svg height="36px" width="34px" viewBox="0 0 36 36" version="1.1" xmlns="http://www.w3.org/2000/svg"><g fill="none" fill-rule="evenodd"><path fill="#FFF" d="M0.5 0.5H35.5V35.5H0.5z"></path><path fill="#55C7F7" fill-rule="nonzero" d="M1 1L35 1 35 13 1 13z"></path><path fill="#7ECF3B" fill-rule="nonzero" d="M1 23L35 23 35 35 1 35z"></path><path fill="#F95F5D" fill-rule="nonzero" d="M13 16L23 16 23 22 13 22z"></path><path fill="#F95F5D" fill-rule="nonzero" d="M1,12 L1,24 L35,24 L35,12 L1,12 Z M24.9275,22.6966292 L11.115,22.6966292 L11.115,13.5730337 L24.9275,13.5730337 L24.9275,22.6966292 Z"></path><path fill="#FDAF42" fill-rule="nonzero" d="M13,1 L23,1 L23,13.835 L13,13.835 L13,1 Z M13,22.4625 L23,22.4625 L23,35 L13,35 L13,22.4625 Z M13,15.28 L23,15.28 L23,21.0175 L13,21.0175 L13,15.28 Z"></path></g></svg>
        <div class="uploading-file">
          <div class="file-left">
            <div class="file-info">
              <span>{{ file.name }}</span>
              <span v-if="file.status === 'uploading'">{{ file.percentage }}</span>
            </div>
            <div class="file-loading">
              <div class="progress" v-if="file.status === 'uploading'">
                <div class="progress-bar" :style="{ width: file.percentage }"></div>
              </div>
              <div class="parsing-success" v-else-if="file.status === 'success'">
                <i class="nodeman-icon nc-check-small"></i>
                {{ $t('上传成功') }}
              </div>
              <div class="parsing-error" v-else-if="file.status === 'error'">
                {{ file.errorMsg }}
              </div>
            </div>
          </div>
          <div class="file-right" v-if="file.status === 'error'">
            <i class="retry nodeman-icon nc-retry" @click="handleRetry"></i>
            <i class="delete nodeman-icon nc-delete" @click="handleAbortUpload"></i>
          </div>
        </div>
      </div>
    </div>
    <div class="upload-accept">
      {{ $t('版本包文件类型') }}
    </div>
  </div>
</template>
<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import Upload from '@/components/setup-table/upload.vue';

@Component({ name: 'UploadMixins' })

export default class UploadMixins extends Mixins(Upload) {}
</script>
<style lang="postcss" scoped>
  @import "@/css/mixins/nodeman.css";

  .upload {
    &-content {
      &-file {
        height: 80px;
        cursor: pointer;
        background: #fafbfd;
        border: 1px dashed #c4c6cc;
        border-radius: 2px;
        position: relative;

        @mixin layout-flex column, center, center;
        &.hover {
          border-color: #3a84ff;
        }
        .file-icon {
          font-size: 24px;
          color: #c4c6cc;
          &.hover {
            color: #3a84ff;
          }
        }
        .file-tips {
          line-height: 1;
          .btn {
            color: #3a84ff;
          }
        }
        .file-input {
          position: absolute;
          left: 0;
          top: 0;
          width: 100%;
          height: 100%;
          cursor: pointer;
          opacity: 0;
        }
      }
      &-info {
        position: relative;
        height: 60px;
        background: #fff;
        border: 1px solid #c4c6cc;
        border-radius: 2px;
        padding: 12px 10px;

        @mixin layout-flex row;
        &.loading {
          &:hover {
            background: #f0f1f5;
          }
        }
        &.error {
          border-color: #ea3636;
          background: rgba(254, 221, 220, .25);
        }
        .abort-icon {
          position: absolute;
          right: 0;
          top: 0;
          font-size: 24px;
          color: #979ba5;
          border-radius: 50%;
          cursor: pointer;
        }
        .uploading-file {
          flex: 1;
          padding: 0 10px;

          @mixin layout-flex row, center, space-between;
          .file-left {
            height: 100%;
            flex: 1;

            @mixin layout-flex column, stretch, space-between;
            .file-info {
              line-height: 1;
              margin-top: 4px;

              @mixin layout-flex row, center, space-between;
            }
            .file-loading {
              line-height: 1;

              @mixin layout-flex row;
              .progress {
                margin-bottom: 4px;
                width: 100%;
                height: 2px;
                background: #dcdee5;
                border-radius: 1px;
                &-bar {
                  height: 2px;
                  border-radius: 1px;
                  background: #3a84ff;
                  transition: width .3s ease-in-out;
                }
              }
              .parsing-success {
                color: #2dcb56;
                height: 16px;

                @mixin layout-flex row, center;
                i {
                  font-size: 24px;
                  margin-left: -6px;
                }
              }
              .parsing-error {
                width: 0;
                flex: 1;
                color: #ea3636;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
              }
            }
          }
          .file-right {
            color: #ea3636;
            cursor: pointer;

            @mixin layout-flex row, center, center;
            .retry {
              margin: 0 6px 2px 0;
            }
            .delete {
              font-size: 24px;
            }
          }
        }
      }
    }
    &-accept {
      line-height: 16px;
      margin-top: 6px;
    }
  }
</style>
