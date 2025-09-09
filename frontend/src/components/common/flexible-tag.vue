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
      v-for="(item, index) in filterList"
      :key="index">
      {{ idKey ? item[idKey] : item }}
    </div>
  </div>
</template>
<script lang="ts">
import { Component, Vue, Prop, Watch } from 'vue-property-decorator';

@Component({ name: 'flexible-tag' })

export default class BkBizSelect extends Vue {
  @Prop({ type: Array, default: () => [] }) private readonly list!: any[];
  @Prop({ type: String, default: '' }) private readonly idKey!: string;
  @Prop({ type: Number, default: 150 }) private readonly maxWidth!: number;

  private numTagNode: any = null;
  private overflowTagIndex = -1;
  private resizeObserver: ResizeObserver | null = null;

  private get filterList() {
    return this.list.filter(item => !!item[this.idKey]);
  }

  private get allTagContext() {
    return this.filterList.map(item => (this.idKey ? item[this.idKey] : item)).join(', ');
  }

  private mounted() {
    this.reCalcOverflow();
    this.initResizeObserver();
  }

  beforeDestroy() {
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
    }
  }

  // 初始化 ResizeObserver
  private initResizeObserver() {
    this.resizeObserver = new ResizeObserver(() => {
      this.reCalcOverflow(); // 监听到尺寸变化时重新计算溢出
    });
    this.resizeObserver.observe(this.$el);
  }

  private reCalcOverflow() {
    this.removeOverflowTagNode();
    if (this.filterList.length < 2) {
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
    this.numTagNode.textContent = `+${this.filterList.length - this.overflowTagIndex}`;
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
  @Watch('list')
  public updateList() {
    this.reCalcOverflow();
  }
}
</script>
