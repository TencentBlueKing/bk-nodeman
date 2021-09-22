<template>
  <div class="check">
    <bk-button ext-cls="check-btn-loading" size="small" v-if="loading" :loading="loading"></bk-button>
    <template v-else>
      <auth-component
        tag="div"
        :authorized="checkAllPermission"
        :apply-info="[{ action }]">
        <template slot-scope="permission">
          <bk-checkbox
            :checked="value === 2"
            :indeterminate="value === 1"
            :class="{
              'all-check': checkType.active === 'all',
              'indeterminate': value === 1 && checkType.active === 'all'
            }"
            :disabled="disabled || permission.disabled"
            v-test.common="'headCheck'"
            @change="handleCheckChange">
          </bk-checkbox>
        </template>
      </auth-component>
      <bk-popover
        ref="popover"
        theme="light agent-operate"
        trigger="click"
        placement="bottom"
        :arrow="false"
        offset="35, 0"
        :on-show="handleOnShow"
        :on-hide="handleOnHide"
        :disabled="disabled">
        <i
          :class="['check-icon nodeman-icon', `nc-arrow-${ isDropDownShow ? 'up' : 'down'}`, { disabled: disabled }]"
          v-test.common="'iconMore'">
        </i>
        <template #content>
          <ul class="dropdown-list" v-test.common="'headCheckUl'">
            <template v-for="(item, index) in checkType.list">
              <auth-component
                tag="li"
                class="list-item"
                style="display: block;"
                :authorized="checkAllPermission || item.id !== 'current'"
                :apply-info="[{ action }]"
                :key="index"
                v-test.common="`moreItem.${item.id}`"
                @click="handleCheckAll(item.id)">
                <template slot-scope="permission">
                  <span :disabled="permission.disabled">
                    {{ item.name }}
                  </span>
                </template>
              </auth-component>
            </template>
          </ul>
        </template>
      </bk-popover>
    </template>
  </div>
</template>
<script lang="ts">
import { CheckValueEnum, ICheckItem } from '@/types';
import { Component, Vue, Prop, Ref, Emit, Watch, Model } from 'vue-property-decorator';

// 表格自定义check列
@Component({ name: 'column-check' })
export default class ColumnCheck extends Vue {
  // 0 未选 1 半选 2 全选
  @Model('update-value', { default: 0, type: Number }) private readonly value!: CheckValueEnum;
  @Prop({ default: false, type: Boolean }) private readonly disabled!: boolean;
  @Prop({ default: false, type: Boolean }) private readonly loading!: boolean;
  @Prop({ default: '', type: String }) private readonly action!: string;
  @Prop({ default: true, type: Boolean }) private readonly checkAllPermission!: boolean;
  @Prop({ default: 'current', type: String }) private readonly defaultCheckType!: 'current' | 'all';

  @Ref('popover') private readonly popover: any;

  // 取消勾选时重置checkType
  @Watch('value')
  private handleValueChange(v: CheckValueEnum) {
    v === CheckValueEnum.uncheck && (this.checkType.active = 'current');
  }

  @Watch('defaultCheckType')
  private handleCheckTypeChange() {
    this.checkType.active = this.defaultCheckType;
  }

  private checkType: {
    active: 'current' | 'all'
    list: ICheckItem[]
  } = {
    active: this.defaultCheckType,
    list: [],
  };
  private isDropDownShow = false;

  private created() {
    this.checkType.list = [
      {
        id: 'current',
        name: this.$t('本页全选') as string,
      },
      {
        id: 'all',
        name: this.$t('跨页全选') as string,
      },
    ];
  }
  /**
   * 全选操作
   * @param {String} type 全选类型：1. 本页权限 2. 跨页全选
   */
  @Emit('change')
  private handleCheckAll(type: 'current' | 'all') {
    this.popover && this.popover.instance.hide();
    this.checkType.active = type;
    this.handleUpdateValue(2);
    return {
      value: CheckValueEnum.checked,
      type,
    };
  }
  /**
   * 勾选事件
   */
  @Emit('change')
  private handleCheckChange(value: boolean) {
    if (!value) {
      this.checkType.active = 'current';
    }
    this.handleUpdateValue(value ? 2 : 0);
    return {
      value: value ? CheckValueEnum.checked : CheckValueEnum.uncheck,
      type: this.checkType.active,
    };
  }
  @Emit('update-value')
  private handleUpdateValue(v: CheckValueEnum) {
    return v;
  }
  private handleOnShow() {
    this.isDropDownShow = true;
  }
  private handleOnHide() {
    this.isDropDownShow = false;
  }
}
</script>
<style lang="postcss" scoped>
@import "@/css/mixins/nodeman.css";

.check {
  text-align: left;
  .all-check {
    >>> .bk-checkbox {
      background-color: #fff;
      &::after {
        border-color: #3a84ff;
      }
    }
  }
  .indeterminate {
    >>> .bk-checkbox {
      &::after {
        background: #3a84ff;
      }
    }
  }
  &-icon {
    position: relative;
    top: 3px;
    font-size: 20px;
    cursor: pointer;
    color: #63656e;
    &.disabled {
      color: #c4c6cc;
    }
  }
  .check-btn-loading {
    padding: 0;
    min-width: auto;
    border: 0;
    text-align: left;
    background: transparent;
    >>> .bk-button-loading {
      position: static;
      transform: translateX(0);
      .bounce4 {
        display: none;
      }
    }
  }
}
</style>
