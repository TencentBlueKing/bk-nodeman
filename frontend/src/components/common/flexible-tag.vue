<template>
  <div
    class="flexible-tag-group"
    v-bk-overflow-tips="{
      content: allTagContext
    }">
    <div
      class="tag-item flexible-tag text-ellipsis"
      :style="{
        maxWidth: `${maxWidth}px`
      }"
      v-for="(item, index) in list"
      :key="index">
      {{ idKey ? item[idKey] : item }}
    </div>
  </div>
</template>
<script lang="ts">
import { Component, Vue, Prop } from 'vue-property-decorator';

@Component({ name: 'flexible-tag' })

export default class BkBizSelect extends Vue {
  @Prop({ type: Array, default: () => [] }) private readonly list!: any[];
  @Prop({ type: String, default: '' }) private readonly idKey!: string;
  @Prop({ type: Number, default: 140 }) private readonly maxWidth!: number;

  private numTagNode: any = null;
  private overflowTagIndex = -1;

  private get allTagContext() {
    return this.list.map(item => (this.idKey ? item[this.idKey] : item)).join(', ');
  }

  private mounted() {
    this.reCalcOverflow();
  }

  private reCalcOverflow() {
    this.removeOverflowTagNode();
    if (this.list.length < 2) {
      return false;
    }
    setTimeout(() => {
      const tags: any[] = this.getTagDOM();
      const tagIndexInSecondRow = tags.findIndex((tagItem, index) => {
        if (!index) {
          return false;
        }
        const previousTag = tags[index - 1];
        return previousTag.offsetTop !== tagItem.offsetTop;
      });
      if (tagIndexInSecondRow > -1) {
        this.overflowTagIndex = tagIndexInSecondRow;
      } else {
        this.overflowTagIndex = -1;
      }
      this.$el.scrollTop = 0;
      this.insertOverflowTag();
    });
  }
  private insertOverflowTag() {
    if (this.overflowTagIndex < 0) {
      return;
    }
    const overflowTagNode = this.getNumTag();
    const referenceTag: any = this.getTagDOM(this.overflowTagIndex);
    if (referenceTag) {
      this.setOverflowTagContent();
      this.$el.insertBefore(overflowTagNode, referenceTag);
    } else {
      this.overflowTagIndex = -1;
      return;
    }
    setTimeout(() => {
      const previousTag: any = this.getTagDOM(this.overflowTagIndex - 1);
      if (overflowTagNode.offsetTop !== previousTag.offsetTop) {
        this.overflowTagIndex -= 1;
        this.$el.insertBefore(overflowTagNode, overflowTagNode.previousSibling);
        this.setOverflowTagContent();
      }
    });
  }
  private setOverflowTagContent() {
    this.numTagNode.textContent = `+${this.list.length - this.overflowTagIndex}`;
  }
  private getTagDOM(index?: number) {
    const tags = [].slice.call(this.$el.querySelectorAll('.tag-item'));
    return typeof index === 'number' ? tags[index] : tags;
  }
  // 创建/获取溢出数字节点
  private getNumTag() {
    if (this.numTagNode) {
      return this.numTagNode;
    }
    const numTagNode = document.createElement('span');
    numTagNode.className = 'num-tag';
    this.numTagNode = numTagNode;
    return numTagNode;
  }
  private removeOverflowTagNode() {
    if (this.numTagNode && this.numTagNode.parentNode === this.$el) {
      this.$el.removeChild(this.numTagNode);
    }
  }
}
</script>
