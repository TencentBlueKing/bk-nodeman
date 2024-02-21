<template>
  <div
    class="flexible-tag-group"
    v-bk-overflow-tips="{
      content: allTagContext
    }">
    <div
      v-for="(item, index) in flexTags"
      :key="index"
      :class="['tag-item flexible-tag text-ellipsis', item.className]"
      :style="{
        maxWidth: `${maxWidth}px`
      }"
      v-bind="item">
      {{ item.tagDisplay }}
    </div>
  </div>
</template>
<script lang="ts">
import { defineComponent, ref, getCurrentInstance, toRefs, PropType, watch } from 'vue';

export default defineComponent({
  props: {
    list: {
      type: Array as PropType<any[]>,
      default: () => [],
    },
    labelKey: {
      type: String,
      default: 'name',
    },
    maxWidth: {
      type: Number,
      default: 140,
    },
    deleteAble: {
      type: Boolean,
      default: false,
    },
  },
  setup(props) {
    const { proxy } = (getCurrentInstance() || {});

    const numTagNode = ref();
    const overflowTagIndex = ref(-4);

    const flexTags = ref<any[]>([]);
    const allTagContext = ref('');

    const removeOverflowTagNode = () => {
      if (proxy?.$el && (numTagNode.value?.parentNode === proxy?.$el)) {
        proxy?.$el.removeChild(numTagNode.value);
      }
    };
    const getTagDOM = (index?: number) => {
      const tags = [].slice.call(proxy?.$el.querySelectorAll('.tag-item'));
      return typeof index === 'number' ? tags[index] : tags;
    };
    // 创建/获取溢出数字节点
    const getNumTag = () => {
      if (numTagNode.value) {
        return numTagNode.value;
      }
      const nodeNum = document.createElement('span');
      nodeNum.className = 'num-tag';
      numTagNode.value = nodeNum;
      return nodeNum;
    };

    const reCalcOverflow = () => {
      removeOverflowTagNode();
      if (props.list.length < 2) {
        return false;
      }
      setTimeout(() => {
        const tags: any[] = getTagDOM();
        const tagIndexInSecondRow = tags.findIndex((tagItem, index) => {
          if (!index) {
            return false;
          }
          const previousTag = tags[index - 1];
          return previousTag.offsetTop !== tagItem.offsetTop;
        });
        if (tagIndexInSecondRow > -1) {
          overflowTagIndex.value = tagIndexInSecondRow;
        } else {
          overflowTagIndex.value = -1;
        }
        if (proxy?.$el) {
          proxy.$el.scrollTop = 0;
        }
        insertOverflowTag();
      });
    };
    const insertOverflowTag = () => {
      if (overflowTagIndex.value < 0) {
        return;
      }
      const overflowTagNode = getNumTag();
      const referenceTag: any = getTagDOM(overflowTagIndex.value);
      if (referenceTag) {
        setOverflowTagContent();
        proxy?.$el.insertBefore(overflowTagNode, referenceTag);
      } else {
        overflowTagIndex.value = -1;
        return;
      }
      setTimeout(() => {
        const previousTag: any = getTagDOM(overflowTagIndex.value - 1);
        if (overflowTagNode.offsetTop !== previousTag.offsetTop) {
          overflowTagIndex.value -= 1;
          proxy?.$el.insertBefore(overflowTagNode, overflowTagNode.previousSibling);
          setOverflowTagContent();
        }
      });
    };
    const setOverflowTagContent = () => {
      numTagNode.value.textContent = `+${props.list.length - overflowTagIndex.value}`;
    };

    const updateTags = () => {
      try {
        const isStr = props.list.length ? typeof props.list[0] === 'string' : false;
        const tags = isStr
          ? props.list.map(text => ({
            tagDisplay: text,
            deleteAble: props.deleteAble,
          }))
          : props.list.map(item => ({
            ...item,
            tagDisplay: item[props.labelKey || 'name'],
            deleteAble: item.readonly ? false : props.deleteAble,
          }));
        flexTags.value.splice(0, flexTags.value.length, ...tags);
        allTagContext.value = tags.map(item => item.tagDisplay).join(', ');
      } catch (_) {
        flexTags.value.splice(0, flexTags.value.length);
        allTagContext.value = '';
      }
    };

    watch(() => props.list, () => {
      updateTags();
      reCalcOverflow();
    }, {
      deep: true,
      immediate: true,
    });

    return {
      ...toRefs(props),
      flexTags,
      allTagContext,
    };
  },
});


</script>
