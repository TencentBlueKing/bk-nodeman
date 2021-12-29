<template>
  <div class="variable-dropdown">
    <bk-input
      v-if="search"
      class="varuabke-input"
      :placeholder="$t('请输入关键字')"
      :left-icon="'bk-icon icon-search'"
      :value="inputSearch"
      v-on="$listeners">
    </bk-input>
    <div class="variable-dropdown-content">
      <ul class="variable-options" :style="`max-height: ${ maxLength * itemHeight }`">
        <li v-if="!variableList.length" class="variable-option-empty">{{ $t('暂无数据') }}</li>
        <li class="variable-option" v-else v-for="(item, index) in variableList" :key="item.key">
          <div class="variable-option-content" @click="handleClick(item, index)">
            <span class="variable-key text-ellipsis">{{ item.key }}</span>
            <span class="variable-desc text-ellipsis ml10">{{ item.description }}</span>
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>
<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';
import { copyText } from '@/common/util';

@Component({ name: 'variable-popover' })
export default class VariablePreview extends Vue {
  @Prop({ type: Boolean, default: false }) private readonly loading!: boolean;
  @Prop({ type: Boolean, default: true }) private readonly search!: boolean;
  @Prop({ type: String, default: '' }) private readonly searchValue!: string;
  @Prop({ type: Boolean, default: true }) private readonly maxLength!: 10;
  @Prop({ type: Boolean, default: false }) private readonly copy!: boolean;
  @Prop({ type: Array, default: () => ([]) }) private readonly list!: {
    [key: string]: string
  }[];

  private itemHeight = 41;
  private inputSearch = '';

  private get variableList() {
    return (this.search && this.searchValue) || this.inputSearch
      ? this.list.filter(item => item.setStr.includes(this.search ? this.searchValue : this.inputSearch))
      : this.list;
  }

  public handleClick(item: Dictionary) {
    if (this.copy) {
      copyText(item.key, () => {
        this.$bkMessage({
          theme: 'success',
          message: this.$t('复制成功'),
        });
      });
    }
    this.$emit('selected', item);
  }
}
</script>
<style lang="postcss" scoped>
  .variable-dropdown {
    display: flex;
    flex-direction: column;
  }
  .variable-dropdown-content {
    width: 400px;
  }
  .varuabke-input {
    margin-bottom: 4px;
    padding: 0 7px;
    >>>.bk-form-input {
      border: 0;
      border-bottom: 1px solid #c4c6cc;
    }
  }
  .variable-options {
    overflow: auto;
    .variable-option-empty {
      line-height: 42px;
      text-align: center;
    }
    .variable-key {
      flex: 1;
      color: #63656e;
    }
    .variable-desc {
      color: #979ba5;
      max-width: 40%;
    }
    .variable-option-content {
      display: flex;
      justify-content: space-between;
      padding: 0 12px;
      line-height: 32px;
      width: 100%;
      font-size: 12px;
      background: #fff;
      &:hover {
        background: #eaf3ff;
        cursor: pointer;
        .variable-key {
          color: #3a84ff;
        }
        .variable-desc {
          color: #699df4;
        }
      }
    }
  }
</style>
