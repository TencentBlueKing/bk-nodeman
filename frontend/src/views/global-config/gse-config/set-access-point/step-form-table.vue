<template>
  <div class="setup">
    <div class="setup-header-wrapper">
      <table>
        <colgroup>
          <col v-for="(item, index) in tableHead" :key="index" :width="item.width ? item.width : 'auto'">
        </colgroup>
        <!-- 表头 -->
        <thead class="setup-header">
          <tr>
            <th v-for="(item, index) in tableHead" :key="index">
              {{ item.name }}
            </th>
          </tr>
        </thead>
      </table>
    </div>
    <div class="setup-body-wrapper">
      <div class="body-content">
        <table class="form-table">
          <colgroup>
            <col v-for="(item, index) in tableHead" :key="index" :width="item.width ? item.width : 'auto'">
          </colgroup>
          <slot name="tbody"></slot>
        </table>
      </div>
    </div>
  </div>
</template>
<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';

@Component({ name: 'setup-form-table' })

export default class SetupFormTable extends Vue {
  @Prop({
    type: Array,
    default: () => ([]),
    validator: v => v && Array.isArray(v),
  }) private readonly tableHead!: { name: string, width?: number }[]; // 安装信息
}
</script>
<style lang="postcss" scoped>
  @import "@/css/mixins/nodeman.css";

  @define-mixin operate-btn {
    font-size: 18px;
    color: #c4c6cc;
    cursor: pointer;
    &:hover {
      color: #979ba5;
    }
  }
  @define-mixin scroll-content {
    position: absolute;
    left: 0;
    top: 0;
    right: 0;
  }

  .setup {
    table {
      table-layout: fixed;
    }
    &-header-wrapper {
      border: 1px solid #dcdee5;
      border-bottom: 0;
      background: #fafbfd;
      .setup-header {
        tr {
          height: 42px;
          font-size: 12px;
          color: #63656e;
          th {
            padding: 0 5px;
            text-align: left;
            font-weight: 400;
            &:first-child {
              padding-left: 16px;
            }
          }
        }
      }
    }
    &-body-wrapper {
      border: 1px solid #dcdee5;
      background: #fff;
      position: relative;
      td {
        border: 1px solid #dcdee5;
      }
      tr td:first-child {
        border-left: 0;
      }
      tr td:last-child {
        border-right: 0;
      }
      tr:first-child td {
        border-top: 0;
      }
    }
  }
</style>
