<template>
  <ul class="topo-tree">
    <li
      class="tree-node-container"
      v-for="node in nodeList"
      v-show="node.show"
      :key="node.id">
      <div
        :class="['tree-node-item', { 'topo-active': node.active }]"
        :style="{ 'padding-left': (26 * (node.level + 1)) + 'px' }"
        @click="handleClickNode(node)">
        <!-- 左侧图标 -->
        <div :class="['node-flex-start', { expanded: node.folded }]">
          <LoadingIcon v-if="node.loading"></LoadingIcon>
          <!-- 节点类型 -->
          <span v-else-if="node.foldable" class="bk-icon icon-right-shape"></span>
        </div>
        <span if="nodeTypeMap[node.topoType]" :class="`word-icon ${ node.topoType }`">
          {{ nodeTypeMap[node.topoType] }}
        </span>
        <span v-bk-overflow-tips class="node-name">{{ node.name }}</span>
        <div v-show="node.topoIcon">
          <i class="nodeman-icon nc-manual" v-bk-tooltips="{
            content: $t('已手动调整资源配额（非默认配置）'),
            boundary: 'window'
          }"></i>
        </div>
      </div>
      <template v-if="node.foldable && node.child && node.child.length">
        <ResourceTreeItem
          v-show="node.folded"
          :node-list="node.child"
          :load-position="loadPosition"
          @click="handleClickNode">
        </ResourceTreeItem>
      </template>
    </li>
  </ul>
</template>

<script lang="ts">
import { Prop, Vue, Component } from 'vue-property-decorator';

interface ITreeNode {
  id: string | number
  name: string | number
  loading: boolean
  active: boolean
  topoType: 'biz' | 'module'
  show: boolean
  level: number
  foldable: boolean
  folded: boolean
  child: ITreeNode[]
}

@Component({
  name: 'ResourceTreeItem',
})
export default class ResourceTreeItem extends Vue {
  @Prop({ type: Array, default: () => [] }) private readonly nodeList!: ITreeNode[];
  @Prop({ type: String, default: 'left' }) private readonly loadPosition!: string;

  public nodeTypeMap = {
    biz: this.$t('业'),
    set: this.$t('集'),
    module: this.$t('模'),
  };

  public handleClickNode(node: ITreeNode) {
    this.$emit('click', node);
  }
}
</script>

<style lang="postcss" scoped>
  .topo-tree {
    width: 100%;

    .tree-node-container {
      .tree-node-item {
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        padding-right: 20px;
        height: 36px;
        line-height: 20px;
        font-size: 14px;
        color: #63656e;
        cursor: pointer;
        transition: background-color .2s;

        &:hover {
          background-color: #e1ecff;
        }

        &:first-child {
          padding-left: 16px!important;
        }

        .node-flex-start {
          /* margin-left: 20px; */
          flex-shrink: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          width: 16px;
          height: 16px;
          font-size: 0;
          cursor: pointer;
          transition: transform .2s;

          &.expanded {
            transform: rotate(90deg);
            transition: transform .2s;
          }

          & + .word-icon,
          & + king-checkbox {
            margin-left: 5px;
          }

          & + .node-name {
            margin-left: 5px;
          }
        }

        .icon-right-shape {
          font-size: 14px;
          color: #c3c6cc;
        }

        .svg-icon {
          width: 14px;
          height: 14px;
        }

        .word-icon {
          flex-shrink: 0;
          width: 20px;
          text-align: center;
          font-size: 12px;
          color: #fff;
          background-color: #c4c6cc;
          border-radius: 50%;

          & + .node-name,
          & + .king-checkbox {
            margin-left: 7px;
          }

          &.module {
            background-color: #97aed6;
          }
        }

        .king-checkbox {
          display: flex;
          align-items: center;
          width: 100%;
          height: 100%;

          /deep/ .bk-checkbox {
            flex-shrink: 0;
          }

          /deep/ .bk-checkbox-text {
            margin-left: 8px;
            width: calc(100% - 24px);
          }
        }

        .node-name {
          flex: 1;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
      }

      .topo-active {
        background: #e1ecff;
        color: #3a84ff;

        .word-icon {
          background-color: #3a84ff !important;
        }

        .node-total-box {
          color: #fff;
          background: #a3c5fd;
        }
      }

      .tree-node-loading {
        display: flex;
        align-items: center;
        width: 100%;
        height: 36px;
        animation: tree-opacity .3s;

        @keyframes tree-opacity {
          0% {
            height: 0;opacity: 0;
          }

          100% {
            opacity: 1;height: 36px;
          }
        }

        .svg-icon {
          width: 16px;
          height: 16px;
        }

        .loading-text {
          font-size: 12px;
          padding-left: 4px;
          color: #a3c5fd;
        }
      }

      .node-child-empty {
        height: 32px;
        line-height: 32px;
        font-size: 12px;
        color: #979ba5;
      }
    }

    .not-topo {
      height: 100%;
      width: 100%;
      color: #63656e;
      display: flex;
      align-items: center;
      justify-content: center;
    }
  }
</style>
