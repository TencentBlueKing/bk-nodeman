<template>
  <ul class="associate-list">
    <li
      class="associate-item"
      v-for="item in list"
      :key="item.id"
      :disabled="item.disabled"
      v-test="{
        testId: item.testId,
        testKey: item.testKey || item.id,
        testAnchor: item.testAnchor || 'common'
      }"
      @click.stop="() => associateItemClick(item.id, item)">
      <div class="associate-item-content">
        <span class="associate-item-text">{{ item.name }}</span>
        <i class="nodeman-icon nc-arrow-right associate-item-icon" v-if="item.child && item.child.length"></i>
      </div>
      <template v-if="item.child && item.child.length">
        <AssociateList
          class="associate-child-list"
          :list="item.child"
          @click="associateItemClick" />
      </template>
    </li>
  </ul>
</template>
<script lang="ts">
import { Component, Vue, Prop } from 'vue-property-decorator';

export interface IAssociateItem {
  id: string | number
  name: string | number
  disabled?: boolean
  testId?: string
  testKey?: string
  testAnchor?: string
  child?: IAssociateItem[]
}

@Component({ name: 'AssociateList' })

export default class AssociateList extends Vue {
  @Prop({ type: Array, default: () => [] }) protected readonly list!: IAssociateItem[];

  public associateItemClick(id: string | number, item: IAssociateItem) {
    this.$emit('click', id, item);
  }
}
</script>
<style lang="postcss">
  .associate-list {
    min-width: 100px;
    white-space: nowrap;

    & .associate-list {
      border-radius: 2px;
      border: 1px solid #dcdee5;
      background: #fff;
      box-shadow: 0 2px 6px rgb(51 60 72 / 10%);
      font-size: 12px;
      color: #63656e;
    }

		.associate-item {
      position: relative;
			line-height: 32px;
			cursor: pointer;

      &::after {
        content: "";
        display: none;
        position: absolute;
        left: 100%;
        top: 0;
        width: 20px;
        height: 100%;
      }

      &:not([disabled="disabled"]):hover {
        background-color: #f5f7fa;
        /* color: #3a84ff; */

        &::after{
          display: block;
        }
        & > .associate-child-list {
          display: block;
        }
      }
      &[disabled="disabled"] {
        background: transparent;
        color: #c4c6cc;
        cursor: not-allowed;
      }
		}
		.associate-child-list {
			display: none;
			position: absolute;
			left: 100%;
			top: -5px;
      margin-top: -1px;
			/* margin-left: 10px; */
      padding: 5px 0;
		}
    .associate-item-content {
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: relative;
			padding: 0 10px 0 12px;
      pointer-events: none;
    }
    .associate-child-list {
      min-width: 60px;
    }
    .associate-item-icon {
      font-size: 16px;
    }
  }
</style>
