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
            :value="checkValue"
            :indeterminate="halfCheck"
            :class="{
              'all-check': checkType.active === 'all',
              'indeterminate': indeterminate && checkType.active === 'all'
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
        :on-hide="handleOnHide">
        <i
          :class="['check-icon nodeman-icon', `nc-arrow-${ isDropDownShow ? 'up' : 'down'}`]"
          v-test.common="'iconMore'">
        </i>
        <template #content>
          <ul class="dropdown-list" v-test.common="'headCheckUl'">
            <template v-for="(item, index) in checkList">
              <auth-component
                tag="li"
                class="list-item"
                style="display: block;"
                v-test.common="`moreItem.${item.id}`"
                :authorized="checkAllPermission || item.id !== 'current'"
                :apply-info="[{ action }]"
                :key="index"
                @click="handleCheckAll(item.id, item.disabled)">
                <template slot-scope="permission">
                  <span :disabled="permission.disabled || item.disabled">
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
<script>
import { bus } from '@/common/bus';
export default {
  name: 'ColumnCheck',
  props: {
    value: {
      type: Boolean,
      default: false,
    },
    // 是否半选
    indeterminate: {
      type: Boolean,
      default: false,
    },
    // 是否全选
    isAllChecked: {
      type: Boolean,
      default: false,
    },
    disabled: {
      type: Boolean,
      default: false,
    },
    loading: {
      type: Boolean,
      default: false,
    },
    action: {
      type: String,
      default: '',
    },
    disabledCheckAll: {
      type: Boolean,
      default: false,
    },
    checkAllPermission: {
      type: Boolean,
      default: true,
    },
  },
  data() {
    return {
      checkValue: this.value,
      checkType: {
        active: 'current',
      },
      isDropDownShow: false,
    };
  },
  computed: {
    halfCheck() {
      return this.indeterminate && !this.isAllChecked;
    },
    checkList() {
      return [
        {
          id: 'current',
          name: this.$t('本页全选'),
        },
        {
          id: 'all',
          disabled: this.disabledCheckAll,
          name: this.$t('跨页全选'),
        },
      ];
    },
  },
  watch: {
    isAllChecked(v) {
      this.checkValue = v;
    },
  },
  mounted() {
    bus.$on('checked-all-agent', () => {
      this.handleCheckAll('all');
    });
    bus.$on('unchecked-all-agent', () => {
      this.handleCheckChange(false);
    });
  },
  methods: {
    /**
     * 全选操作
     * @param {String} type 全选类型：1. 本页权限 2. 跨页全选
     */
    handleCheckAll(type, disabled = false) {
      if (!disabled) {
        this.$refs.popover && this.$refs.popover.instance.hide();
        this.checkType.active = type;
        this.$emit('change', true, type);
      }
    },
    /**
     * 勾选事件
     */
    handleCheckChange(value) {
      this.checkValue = value;
      if (!value) {
        this.checkType.active = 'current';
      }
      this.$emit('change', this.checkValue, this.checkType.active);
    },
    handleOnShow() {
      this.isDropDownShow = true;
    },
    handleOnHide() {
      this.isDropDownShow = false;
    },
  },
};
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
